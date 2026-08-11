from datetime import datetime

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string

from appointments.models import Appointment
from .models import Reminder


def auto_sync_appointment_reminders():
    """Ensure a Reminder log exists for every Confirmed, Rescheduled, Cancelled, or No-Show appointment."""
    relevant_statuses = ['Confirmed', 'Rescheduled', 'Cancelled', 'No-Show']
    type_map = {
        'Confirmed': 'Confirmation',
        'Rescheduled': 'Reschedule Notice',
        'Cancelled': 'Cancellation Notice',
        'No-Show': 'No-Show Notice',
    }
    target_appointments = Appointment.objects.filter(status__in=relevant_statuses)

    for appt in target_appointments:
        rem_type = type_map.get(appt.status, 'Confirmation')
        scheduled_dt = datetime.combine(appt.appointment_date, appt.start_time)
        existing = Reminder.objects.filter(appointment=appt).first()
        if not existing:
            Reminder.objects.create(
                appointment=appt,
                reminder_type=rem_type,
                channel='Email',
                scheduled_for=scheduled_dt,
                status='Pending',
                message=f"Email notification for appointment {appt.appointment_id} ({appt.status})",
            )
        else:
            if existing.status == 'Pending' and existing.reminder_type != rem_type:
                existing.reminder_type = rem_type
                existing.scheduled_for = scheduled_dt
                existing.message = f"Email notification for appointment {appt.appointment_id} ({appt.status})"
                existing.save()


@login_required
def reminder_list(request):
    if not (request.user.is_admin() or request.user.is_staff_role()):
        reminders = Reminder.objects.filter(appointment__patient__user=request.user).order_by('-created_at')
        return render(request, 'dashboard/reminders.html', {'reminders': reminders, 'is_admin_view': False})

    auto_sync_appointment_reminders()

    tab = request.GET.get('tab', 'all')
    q = request.GET.get('q', '').strip()

    reminders = Reminder.objects.select_related(
        'appointment',
        'appointment__patient',
        'appointment__patient__user',
        'appointment__dentist',
        'appointment__dentist__user',
        'appointment__service',
    ).all()

    if tab == 'confirmed':
        reminders = reminders.filter(appointment__status='Confirmed')
    elif tab == 'rescheduled':
        reminders = reminders.filter(appointment__status='Rescheduled')
    elif tab == 'cancelled':
        reminders = reminders.filter(appointment__status='Cancelled')
    elif tab == 'no_show':
        reminders = reminders.filter(appointment__status='No-Show')
    elif tab == 'pending_mail':
        reminders = reminders.filter(status='Pending')
    elif tab == 'sent_mail':
        reminders = reminders.filter(status='Sent')
    elif tab == 'failed_mail':
        reminders = reminders.filter(status='Failed')

    if q:
        reminders = reminders.filter(
            Q(appointment__appointment_id__icontains=q) |
            Q(appointment__patient__user__first_name__icontains=q) |
            Q(appointment__patient__user__last_name__icontains=q) |
            Q(appointment__patient__user__email__icontains=q) |
            Q(appointment__dentist__user__first_name__icontains=q) |
            Q(appointment__dentist__user__last_name__icontains=q) |
            Q(appointment__status__icontains=q) |
            Q(reminder_type__icontains=q)
        )

    reminders = reminders.order_by('-created_at')

    all_reminders = Reminder.objects.all()
    counts = {
        'all': all_reminders.count(),
        'confirmed': all_reminders.filter(appointment__status='Confirmed').count(),
        'rescheduled': all_reminders.filter(appointment__status='Rescheduled').count(),
        'cancelled': all_reminders.filter(appointment__status='Cancelled').count(),
        'no_show': all_reminders.filter(appointment__status='No-Show').count(),
        'pending_mail': all_reminders.filter(status='Pending').count(),
        'sent_mail': all_reminders.filter(status='Sent').count(),
        'failed_mail': all_reminders.filter(status='Failed').count(),
    }

    return render(request, 'dashboard/reminders.html', {
        'reminders': reminders,
        'tab': tab,
        'q': q,
        'counts': counts,
        'is_admin_view': True,
    })


@login_required
def send_reminder_email(request, pk):
    if not (request.user.is_admin() or request.user.is_staff_role()):
        messages.error(request, 'Permission denied. Only clinic administrators can dispatch reminder emails.')
        return redirect('reminders')

    reminder = get_object_or_404(Reminder, pk=pk)
    appointment = reminder.appointment
    patient_user = appointment.patient.user
    patient_email = patient_user.email
    patient_name = patient_user.get_full_name() or patient_user.username

    if not patient_email:
        reminder.status = 'Failed'
        reminder.error_message = 'Patient does not have a registered email address.'
        reminder.save()
        messages.error(request, f"Cannot send email: Patient {patient_name} does not have an email address.")
        return redirect('reminders')

    subject_map = {
        'Confirmed': f"[SmileCare Dental] Appointment Confirmed - ID: {appointment.appointment_id}",
        'Rescheduled': f"[SmileCare Dental] Appointment Rescheduled - ID: {appointment.appointment_id}",
        'Cancelled': f"[SmileCare Dental] Appointment Cancellation Notice - ID: {appointment.appointment_id}",
        'No-Show': f"[SmileCare Dental] Important Notice Regarding Your Appointment - ID: {appointment.appointment_id}",
    }
    subject = subject_map.get(appointment.status, f"[SmileCare Dental] Appointment Update - ID: {appointment.appointment_id}")

    context = {
        'appointment': appointment,
        'patient_name': patient_name,
    }

    html_content = render_to_string('emails/appointment_notification.html', context)
    text_content = render_to_string('emails/appointment_notification.txt', context)

    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'uniquebiwas@gmail.com')

    try:
        msg = EmailMultiAlternatives(subject, text_content, from_email, [patient_email])
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)

        reminder.status = 'Sent'
        reminder.sent_at = datetime.now()
        reminder.error_message = ''
        reminder.save()

        # ── Push live WebSocket notification to the patient ──
        try:
            channel_layer = get_channel_layer()
            group_name = f"notifications_{patient_user.pk}"
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    "type": "send_notification",
                    "title": "📧 Appointment Notification Sent",
                    "message": f"A confirmation email was sent for Appointment {appointment.appointment_id}.",
                    "notification_type": "info",
                }
            )
        except Exception:
            pass  # WebSocket push failure must never break the email flow

        messages.success(
            request,
            f"Email notification successfully sent to {patient_email} for Appointment {appointment.appointment_id}."
        )
    except Exception as e:
        raw_error = str(e).strip()
        if "AuthenticationFailed" in raw_error or "535" in raw_error or "Username and Password not accepted" in raw_error:
            clean_error = "Gmail SMTP Authentication Failed. Please verify App Password."
        elif "ConnectionRefusedError" in raw_error or "10061" in raw_error or "timed out" in raw_error or "getaddrinfo" in raw_error:
            clean_error = "Network Error: Unable to reach smtp.gmail.com."
        else:
            clean_error = raw_error.split('\n')[0][:120] if raw_error else "SMTP Transmission Error."

        reminder.status = 'Failed'
        reminder.error_message = clean_error
        reminder.save()

        messages.error(
            request,
            f"Failed to send email to {patient_email}: {clean_error}"
        )

    return redirect('reminders')
