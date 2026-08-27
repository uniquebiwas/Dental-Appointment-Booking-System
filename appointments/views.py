from datetime import datetime, timedelta, time

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import User
from dentists.models import Dentist, DentistAvailability
from patients.models import Patient
from reminders.models import Notification
from services.models import DentalService
from .models import Appointment, AppointmentHistory, PatientVisit


def _push_ws_notification(user_pk, title, message, notif_type='appointment'):
    """Non-blocking helper – silently ignores errors."""
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"notifications_{user_pk}",
            {
                "type": "send_notification",
                "title": title,
                "message": message,
                "notification_type": notif_type,
            }
        )
    except Exception:
        pass

def get_available_slots(dentist, date_obj, duration_minutes):
    available_slots = []
    unavailable_slots = []
    availability_source = 'dentist'
    day_of_week = date_obj.isoweekday()
    availabilities = list(DentistAvailability.objects.filter(dentist=dentist, day_of_week=day_of_week, active=True))
    if not availabilities:
        availability_source = 'default'
        availabilities = [type('DefaultAvailability', (), {'start_time': time(10, 0), 'end_time': time(17, 0)})]

    booked_appointments = Appointment.objects.filter(dentist=dentist, appointment_date=date_obj).exclude(status='Cancelled')
    slot_length = timedelta(minutes=max(duration_minutes, 30))

    now = datetime.now()
    today = now.date()
    for availability in availabilities:
        current = datetime.combine(date_obj, availability.start_time)
        end_period = datetime.combine(date_obj, availability.end_time)
        break_start = datetime.combine(date_obj, availability.break_start) if getattr(availability, 'break_start', None) else None
        break_end = datetime.combine(date_obj, availability.break_end) if getattr(availability, 'break_end', None) else None
        while current + slot_length <= end_period:
            if break_start and break_end and current >= break_start and current < break_end:
                current = break_end
                continue
            slot_start = current.time()
            slot_end = (current + slot_length).time()
            slot_start_dt = datetime.combine(date_obj, slot_start)
            if date_obj == today and slot_start_dt <= now:
                current += slot_length
                continue
            if break_start and break_end and datetime.combine(date_obj, slot_end) > break_start and slot_start_dt < break_start:
                current = break_end
                continue
            conflict = booked_appointments.filter(start_time__lt=slot_end, end_time__gt=slot_start).exists()
            slot_label = slot_start.strftime('%H:%M')
            if conflict:
                unavailable_slots.append(slot_label)
            else:
                available_slots.append(slot_label)
            current += slot_length

    return available_slots, unavailable_slots, availability_source


def validate_appointment_slot(dentist, service, date_obj, start_time):
    if not start_time:
        return None, None, 'Select a time slot for the appointment.'
    if date_obj < datetime.now().date():
        return None, None, 'Appointment date cannot be in the past.'
    try:
        time_obj = datetime.strptime(start_time, '%H:%M').time()
    except (ValueError, TypeError):
        return None, None, 'Select a valid time slot from the list.'

    appointment_start = datetime.combine(date_obj, time_obj)
    if appointment_start <= datetime.now():
        return None, None, 'Cannot schedule an appointment in the past. Choose a future date and time.'

    slot_length = timedelta(minutes=service.duration or 30)
    end_time = (appointment_start + slot_length).time()
    if end_time <= time_obj:
        return None, None, 'Selected slot and service duration cannot cross midnight. Please choose an earlier slot or another date.'

    available_slots, _, _ = get_available_slots(dentist, date_obj, service.duration or 30)
    if start_time not in available_slots:
        return None, None, 'Selected time slot is not available. Please choose a valid slot.'

    conflict = Appointment.objects.filter(dentist=dentist, appointment_date=date_obj).exclude(status='Cancelled').filter(
        start_time__lt=end_time,
        end_time__gt=time_obj,
    ).exists()
    if conflict:
        return None, None, 'That slot is no longer available.'

    return time_obj, end_time, None


def ensure_default_weekly_availability(dentist):
    for day in range(1, 8):
        DentistAvailability.objects.get_or_create(
            dentist=dentist,
            day_of_week=day,
            defaults={
                'start_time': time(10, 0),
                'end_time': time(17, 0),
                'active': True,
            }
        )


@login_required
def book_appointment(request):
    approved_dentist_users = User.objects.filter(role='dentist', account_status='approved', is_active=True)
    for dentist_user in approved_dentist_users:
        dentist, created = Dentist.objects.get_or_create(
            user=dentist_user,
            defaults={
                'dentist_id': f'DNT-{dentist_user.pk:04d}',
                'specialization': 'General Dentistry',
                'license_number': f'LIC-{dentist_user.pk:06d}',
                'phone': dentist_user.phone or '',
                'active': True,
            }
        )
        ensure_default_weekly_availability(dentist)
    dentists = Dentist.objects.filter(active=True, user__is_active=True, user__account_status='approved').order_by('user__first_name', 'user__last_name')
    services = DentalService.objects.filter(active=True)
    patients = None
    selected_patient_pk = None
    selected_dentist = None
    selected_service = None
    selected_date = None
    selected_start_time = None
    patient_search = ''
    available_slots = []
    unavailable_slots = []
    availability_source = None

    if request.user.is_staff_role() and not request.user.is_admin():
        patients = Patient.objects.select_related('user').all()

    if request.method == 'POST':
        dentist_id = request.POST.get('dentist')
        service_id = request.POST.get('service')
        appointment_date = request.POST.get('appointment_date')
        start_time = request.POST.get('start_time')
        reason = request.POST.get('reason')
        selected_start_time = start_time
        patient_pk = request.POST.get('patient') if request.user.is_staff_role() and not request.user.is_admin() else None

        if request.user.is_staff_role() and not request.user.is_admin():
            if not patient_pk:
                messages.error(request, 'Select a patient before booking.')
                patient = None
            else:
                patient = get_object_or_404(Patient, pk=patient_pk)
                selected_patient_pk = patient.pk
        else:
            patient = Patient.objects.filter(user=request.user).first()
            if patient:
                selected_patient_pk = patient.pk

        if not patient:
            messages.error(request, 'Create a patient profile before booking.')
            return redirect('patient_profile')

        dentist = get_object_or_404(Dentist, pk=dentist_id)
        service = get_object_or_404(DentalService, pk=service_id)
        selected_dentist = dentist
        selected_service = service
        selected_date = appointment_date

        try:
            date_obj = datetime.strptime(appointment_date, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            date_obj = None
            messages.error(request, 'Enter a valid appointment date.')

        if date_obj:
            time_obj, end_time, slot_error = validate_appointment_slot(dentist, service, date_obj, start_time)
            if slot_error:
                messages.error(request, slot_error)
            else:
                appointment = Appointment.objects.create(
                    appointment_id=f'APT-{datetime.now().strftime("%Y%m%d%H%M%S")}',
                    patient=patient,
                    dentist=dentist,
                    service=service,
                    appointment_date=date_obj,
                    start_time=time_obj,
                    end_time=end_time,
                    reason=reason,
                    status='Pending',
                )
                AppointmentHistory.objects.create(
                    appointment=appointment,
                    previous_status='New',
                    new_status='Pending',
                    changed_by=request.user,
                    reason='Appointment booked',
                )
                # Create DB Notification + WS push for dentist
                notif_title = f"New Appointment Booked — {appointment.appointment_id}"
                notif_msg = (
                    f"A new appointment has been booked for "
                    f"{patient.user.get_full_name() or patient.user.username} on "
                    f"{date_obj.strftime('%b. %d, %Y')} at {time_obj.strftime('%I:%M %p')}."
                )
                Notification.objects.create(
                    user=dentist.user,
                    appointment=appointment,
                    title=notif_title,
                    message=notif_msg,
                    notification_type='appointment',
                )
                _push_ws_notification(dentist.user.pk, notif_title, notif_msg)
                # Notify staff/admin too
                for staff_user in User.objects.filter(role__in=['staff', 'admin'], is_active=True):
                    Notification.objects.create(
                        user=staff_user,
                        appointment=appointment,
                        title=notif_title,
                        message=notif_msg,
                        notification_type='appointment',
                    )
                    _push_ws_notification(staff_user.pk, notif_title, notif_msg)
                messages.success(request, 'Appointment created successfully for %s.' % (patient.user.get_full_name() or patient.user.username))
                return redirect('appointment_detail', pk=appointment.pk)

        if selected_dentist and selected_service and appointment_date:
            try:
                date_obj = datetime.strptime(appointment_date, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                date_obj = None
            if date_obj:
                available_slots, unavailable_slots, availability_source = get_available_slots(dentist, date_obj, service.duration or 30)
                if selected_start_time and selected_start_time not in available_slots:
                    selected_start_time = None

    elif request.method == 'GET':
        dentist_id = request.GET.get('dentist')
        service_id = request.GET.get('service')
        appointment_date = request.GET.get('appointment_date')
        selected_patient_pk = request.GET.get('patient')
        patient_search = request.GET.get('patient_search', '').strip()

        if request.user.is_staff_role() and not request.user.is_admin() and patient_search:
            patients = patients.filter(
                Q(patient_id__icontains=patient_search) |
                Q(user__first_name__icontains=patient_search) |
                Q(user__last_name__icontains=patient_search) |
                Q(user__email__icontains=patient_search) |
                Q(user__username__icontains=patient_search)
            )

        if dentist_id:
            selected_dentist = Dentist.objects.filter(pk=dentist_id).first()
        if service_id:
            selected_service = DentalService.objects.filter(pk=service_id).first()
        if appointment_date:
            selected_date = appointment_date

        if selected_dentist and selected_service and selected_date:
            try:
                date_obj = datetime.strptime(appointment_date, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                date_obj = None
            if date_obj:
                available_slots, unavailable_slots, availability_source = get_available_slots(selected_dentist, date_obj, selected_service.duration or 30)

    return render(request, 'dashboard/book_appointment.html', {
        'dentists': dentists,
        'services': services,
        'patients': patients,
        'selected_patient_pk': selected_patient_pk,
        'selected_dentist': selected_dentist,
        'selected_service': selected_service,
        'selected_date': selected_date,
        'selected_start_time': selected_start_time,
        'available_slots': available_slots,
        'unavailable_slots': unavailable_slots,
        'availability_source': availability_source,
        'patient_search': patient_search,
    })


@login_required
def appointment_detail(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    can_view = (
        request.user.is_admin()
        or request.user.is_staff_role()
        or request.user == appointment.patient.user
        or (request.user.is_dentist_approved() and request.user == appointment.dentist.user)
    )
    if not can_view:
        return redirect('patient_dashboard')

    if request.method == 'POST' and request.user.is_dentist_approved() and request.user == appointment.dentist.user:
        previous_status = appointment.status
        notes = request.POST.get('notes', '').strip()
        status = request.POST.get('status')
        status_changed = False
        notes_updated = False
        if status in ['Pending', 'Confirmed', 'Checked-In', 'Completed', 'Cancelled', 'Rescheduled', 'No-Show'] and status != appointment.status:
            appointment.status = status
            status_changed = True
        if notes and (appointment.status == 'Completed' or status == 'Completed'):
            appointment.notes = notes
            notes_updated = True
        appointment.save()
        AppointmentHistory.objects.create(
            appointment=appointment,
            previous_status=previous_status,
            new_status=appointment.status,
            changed_by=request.user,
            reason='Dentist feedback updated',
        )
        if status_changed or notes_updated:
            dentist_name = request.user.get_full_name() or request.user.username
            title = f"Appointment {appointment.appointment_id} updated"
            message = f"{dentist_name} updated appointment {appointment.appointment_id}."
            if status_changed:
                message += f" Status changed from {previous_status} to {appointment.status}."
            if notes_updated:
                message += " Comments have been added by the dentist."
            Notification.objects.create(
                user=appointment.patient.user,
                appointment=appointment,
                title=title,
                message=message,
                notification_type='appointment',
            )
            # Live WebSocket push to patient
            _push_ws_notification(appointment.patient.user.pk, title, message)

            staff_users = User.objects.filter(role__in=['staff', 'admin'], is_active=True)
            for staff_user in staff_users:
                Notification.objects.create(
                    user=staff_user,
                    appointment=appointment,
                    title=title,
                    message=message,
                    notification_type='appointment',
                )
                # Live WebSocket push to each staff/admin
                _push_ws_notification(staff_user.pk, title, message)
        messages.success(request, 'Dentist feedback saved.')
        return redirect('appointment_detail', pk=pk)

    appointment_start = datetime.combine(appointment.appointment_date, appointment.start_time)
    can_cancel_reschedule = appointment_start >= datetime.now() and appointment.status not in ['Cancelled', 'Completed', 'No-Show']
    return render(request, 'dashboard/appointment_detail.html', {
        'appointment': appointment,
        'can_cancel_reschedule': can_cancel_reschedule,
    })


@login_required
def appointment_history(request):
    q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    if request.user.is_admin() or request.user.is_staff_role():
        appointments = Appointment.objects.all()
    elif request.user.is_dentist_approved():
        appointments = Appointment.objects.filter(dentist__user=request.user)
    else:
        appointments = Appointment.objects.filter(patient__user=request.user)
    if q:
        appointments = appointments.filter(
            Q(appointment_id__icontains=q) |
            Q(patient__user__first_name__icontains=q) |
            Q(patient__user__last_name__icontains=q) |
            Q(dentist__user__first_name__icontains=q) |
            Q(dentist__user__last_name__icontains=q) |
            Q(status__icontains=q) |
            Q(service__name__icontains=q)
        )
    if status_filter:
        appointments = appointments.filter(status=status_filter)
    if date_from:
        try:
            from datetime import date as _date
            appointments = appointments.filter(appointment_date__gte=datetime.strptime(date_from, '%Y-%m-%d').date())
        except ValueError:
            pass
    if date_to:
        try:
            from datetime import date as _date
            appointments = appointments.filter(appointment_date__lte=datetime.strptime(date_to, '%Y-%m-%d').date())
        except ValueError:
            pass
    appointments = appointments.order_by('-appointment_date', '-start_time')
    status_choices = ['Pending', 'Confirmed', 'Checked-In', 'Completed', 'Cancelled', 'Rescheduled', 'No-Show']
    return render(request, 'dashboard/appointment_history.html', {
        'appointments': appointments,
        'q': q,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'status_choices': status_choices,
    })


@login_required
def cancel_appointment(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    appointment_start = datetime.combine(appointment.appointment_date, appointment.start_time)
    if appointment_start < datetime.now() or appointment.status in ['Cancelled', 'Completed', 'No-Show']:
        messages.error(request, 'Past or already finalized appointments cannot be canceled.')
        return redirect('appointment_detail', pk=appointment.pk)

    if request.method == 'POST':
        previous_status = appointment.status
        cancellation_reason = request.POST.get('reason', 'No reason provided')
        appointment.status = 'Cancelled'
        appointment.cancellation_reason = cancellation_reason
        appointment.cancelled_at = datetime.now()
        appointment.save()
        AppointmentHistory.objects.create(
            appointment=appointment,
            previous_status=previous_status,
            new_status='Cancelled',
            changed_by=request.user,
            reason=cancellation_reason
        )

        # Notifications for cancellation
        cancelled_by_name = request.user.get_full_name() or request.user.username
        cancel_title = f"Appointment {appointment.appointment_id} Cancelled"
        cancel_msg = (
            f"{cancelled_by_name} cancelled appointment {appointment.appointment_id} "
            f"(originally on {appointment.appointment_date.strftime('%b. %d, %Y')} "
            f"at {appointment.start_time.strftime('%I:%M %p')}). "
            f"Reason: {cancellation_reason}"
        )

        # 1. Notify Dentist (unless dentist is the one cancelling)
        if appointment.dentist and appointment.dentist.user and appointment.dentist.user != request.user:
            Notification.objects.create(
                user=appointment.dentist.user,
                appointment=appointment,
                title=cancel_title,
                message=cancel_msg,
                notification_type='appointment',
            )
            _push_ws_notification(appointment.dentist.user.pk, cancel_title, cancel_msg)

        # 2. Notify Patient (unless patient is the one cancelling)
        if appointment.patient and appointment.patient.user and appointment.patient.user != request.user:
            Notification.objects.create(
                user=appointment.patient.user,
                appointment=appointment,
                title=cancel_title,
                message=cancel_msg,
                notification_type='appointment',
            )
            _push_ws_notification(appointment.patient.user.pk, cancel_title, cancel_msg)

        # 3. Notify Staff and Admin (excluding the actor)
        for staff_user in User.objects.filter(role__in=['staff', 'admin'], is_active=True).exclude(pk=request.user.pk):
            Notification.objects.create(
                user=staff_user,
                appointment=appointment,
                title=cancel_title,
                message=cancel_msg,
                notification_type='appointment',
            )
            _push_ws_notification(staff_user.pk, cancel_title, cancel_msg)

        messages.success(request, 'Appointment cancelled.')
        return redirect('appointment_detail', pk=appointment.pk)
    return render(request, 'dashboard/cancel_appointment.html', {'appointment': appointment})


@login_required
def reschedule_appointment(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    appointment_start = datetime.combine(appointment.appointment_date, appointment.start_time)
    if appointment_start < datetime.now() or appointment.status in ['Cancelled', 'Completed', 'No-Show']:
        messages.error(request, 'Past or already finalized appointments cannot be rescheduled.')
        return redirect('appointment_detail', pk=appointment.pk)

    selected_date = appointment.appointment_date
    selected_start_time = appointment.start_time.strftime('%H:%M')
    available_slots = get_available_slots(appointment.dentist, selected_date, appointment.service.duration or 30)[0]

    if request.method == 'POST':
        new_date = request.POST.get('appointment_date')
        new_time = request.POST.get('start_time')
        selected_start_time = new_time
        try:
            date_obj = datetime.strptime(new_date, '%Y-%m-%d').date()
            selected_date = date_obj
        except (ValueError, TypeError):
            date_obj = None
            messages.error(request, 'Enter a valid appointment date.')

        if date_obj:
            time_obj, end_time, slot_error = validate_appointment_slot(appointment.dentist, appointment.service, date_obj, new_time)
            if slot_error:
                messages.error(request, slot_error)
                available_slots = get_available_slots(appointment.dentist, date_obj, appointment.service.duration or 30)[0]
            else:
                previous_status = appointment.status
                previous_date_str = appointment.appointment_date.strftime('%b. %d, %Y')
                previous_time_str = f"{appointment.start_time.strftime('%I:%M %p')} - {appointment.end_time.strftime('%I:%M %p')}"
                appointment.appointment_date = date_obj
                appointment.start_time = time_obj
                appointment.end_time = end_time
                appointment.status = 'Rescheduled'
                appointment.save()
                AppointmentHistory.objects.create(
                    appointment=appointment,
                    previous_status=previous_status,
                    new_status='Rescheduled',
                    changed_by=request.user,
                    reason='Appointment rescheduled',
                )

                # Send notifications to Dentist, Patient, and Staff/Admin
                rescheduled_by_name = request.user.get_full_name() or request.user.username
                new_date_str = date_obj.strftime('%b. %d, %Y')
                new_time_str = f"{time_obj.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')}"
                title = f"Appointment {appointment.appointment_id} Rescheduled"
                message = (
                    f"{rescheduled_by_name} rescheduled appointment {appointment.appointment_id} "
                    f"from {previous_date_str} ({previous_time_str}) to {new_date_str} ({new_time_str})."
                )

                # 1. Notify Dentist
                if appointment.dentist and appointment.dentist.user:
                    Notification.objects.create(
                        user=appointment.dentist.user,
                        appointment=appointment,
                        title=title,
                        message=message,
                        notification_type='appointment',
                    )
                    _push_ws_notification(appointment.dentist.user.pk, title, message)

                # 2. Notify Patient (if not rescheduled by patient themselves or if patient user exists)
                if appointment.patient and appointment.patient.user and appointment.patient.user != request.user:
                    Notification.objects.create(
                        user=appointment.patient.user,
                        appointment=appointment,
                        title=title,
                        message=message,
                        notification_type='appointment',
                    )
                    _push_ws_notification(appointment.patient.user.pk, title, message)

                # 3. Notify Staff and Admin users (excluding current actor if applicable)
                staff_users = User.objects.filter(role__in=['staff', 'admin'], is_active=True).exclude(pk=request.user.pk)
                for staff_user in staff_users:
                    Notification.objects.create(
                        user=staff_user,
                        appointment=appointment,
                        title=title,
                        message=message,
                        notification_type='appointment',
                    )
                    _push_ws_notification(staff_user.pk, title, message)

                messages.success(request, 'Appointment rescheduled.')
                return redirect('appointment_detail', pk=appointment.pk)

    return render(request, 'dashboard/reschedule_appointment.html', {
        'appointment': appointment,
        'available_slots': available_slots,
        'selected_date': selected_date,
        'selected_start_time': selected_start_time,
    })


@login_required
def staff_dashboard(request):
    today = Appointment.objects.filter(appointment_date=datetime.now().date()).order_by('start_time')
    confirmed = Appointment.objects.filter(status='Confirmed').count()
    pending = Appointment.objects.filter(status='Pending').count()
    cancelled = Appointment.objects.filter(status='Cancelled').count()
    no_shows = Appointment.objects.filter(status='No-Show').count()
    return render(request, 'dashboard/staff_dashboard.html', {'today': today, 'confirmed': confirmed, 'pending': pending, 'cancelled': cancelled, 'no_shows': no_shows})
