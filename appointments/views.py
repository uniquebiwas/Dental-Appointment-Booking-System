from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from dentists.models import Dentist, DentistAvailability
from patients.models import Patient
from services.models import DentalService
from .models import Appointment, AppointmentHistory, PatientVisit


@login_required
def book_appointment(request):
    dentists = Dentist.objects.filter(active=True)
    services = DentalService.objects.filter(active=True)
    if request.method == 'POST':
        dentist_id = request.POST.get('dentist')
        service_id = request.POST.get('service')
        appointment_date = request.POST.get('appointment_date')
        start_time = request.POST.get('start_time')
        reason = request.POST.get('reason')
        patient = Patient.objects.filter(user=request.user).first()
        if not patient:
            messages.error(request, 'Create a patient profile before booking.')
            return redirect('patient_profile')
        dentist = get_object_or_404(Dentist, pk=dentist_id)
        service = get_object_or_404(DentalService, pk=service_id)
        date_obj = datetime.strptime(appointment_date, '%Y-%m-%d').date()
        time_obj = datetime.strptime(start_time, '%H:%M').time()
        end_time = (datetime.combine(date_obj, time_obj) + timedelta(minutes=service.duration)).time()
        conflicts = Appointment.objects.filter(dentist=dentist, appointment_date=date_obj).filter(
            start_time__lt=end_time,
            end_time__gt=time_obj,
        )
        if conflicts.exists():
            messages.error(request, 'That slot is no longer available.')
            return redirect('book_appointment')
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
        AppointmentHistory.objects.create(appointment=appointment, previous_status='New', new_status='Pending', changed_by=request.user, reason='Appointment booked')
        messages.success(request, 'Appointment created successfully.')
        return redirect('appointment_detail', pk=appointment.pk)
    return render(request, 'dashboard/book_appointment.html', {'dentists': dentists, 'services': services})


@login_required
def appointment_detail(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    if request.user.is_admin() or request.user.is_staff_role() or request.user == appointment.patient.user:
        return render(request, 'dashboard/appointment_detail.html', {'appointment': appointment})
    return redirect('patient_dashboard')


@login_required
def appointment_history(request):
    appointments = Appointment.objects.filter(patient__user=request.user).order_by('-appointment_date', '-start_time')
    return render(request, 'dashboard/appointment_history.html', {'appointments': appointments})


@login_required
def cancel_appointment(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    if request.method == 'POST':
        appointment.status = 'Cancelled'
        appointment.cancellation_reason = request.POST.get('reason', 'No reason provided')
        appointment.cancelled_at = datetime.now()
        appointment.save()
        AppointmentHistory.objects.create(appointment=appointment, previous_status=appointment.status, new_status='Cancelled', changed_by=request.user, reason=appointment.cancellation_reason)
        messages.success(request, 'Appointment cancelled.')
        return redirect('appointment_detail', pk=appointment.pk)
    return render(request, 'dashboard/cancel_appointment.html', {'appointment': appointment})


@login_required
def reschedule_appointment(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    if request.method == 'POST':
        new_date = request.POST.get('appointment_date')
        new_time = request.POST.get('start_time')
        date_obj = datetime.strptime(new_date, '%Y-%m-%d').date()
        time_obj = datetime.strptime(new_time, '%H:%M').time()
        appointment.appointment_date = date_obj
        appointment.start_time = time_obj
        appointment.end_time = (datetime.combine(date_obj, time_obj) + timedelta(minutes=appointment.service.duration)).time()
        appointment.status = 'Rescheduled'
        appointment.save()
        AppointmentHistory.objects.create(appointment=appointment, previous_status='Pending', new_status='Rescheduled', changed_by=request.user, reason='Appointment rescheduled')
        messages.success(request, 'Appointment rescheduled.')
        return redirect('appointment_detail', pk=appointment.pk)
    return render(request, 'dashboard/reschedule_appointment.html', {'appointment': appointment})


@login_required
def staff_dashboard(request):
    today = Appointment.objects.filter(appointment_date=datetime.now().date()).order_by('start_time')
    confirmed = Appointment.objects.filter(status='Confirmed').count()
    pending = Appointment.objects.filter(status='Pending').count()
    cancelled = Appointment.objects.filter(status='Cancelled').count()
    no_shows = Appointment.objects.filter(status='No-Show').count()
    return render(request, 'dashboard/staff_dashboard.html', {'today': today, 'confirmed': confirmed, 'pending': pending, 'cancelled': cancelled, 'no_shows': no_shows})
