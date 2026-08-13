from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from appointments.models import Appointment
from .forms import PatientProfileForm
from .models import Patient


@login_required
def patient_dashboard(request):
    patient = Patient.objects.filter(user=request.user).first()
    upcoming = Appointment.objects.filter(patient=patient, status__in=['Pending', 'Confirmed', 'Checked-In']).order_by('appointment_date', 'start_time') if patient else Appointment.objects.none()
    history = Appointment.objects.filter(patient=patient).exclude(status__in=['Pending', 'Confirmed', 'Checked-In']).order_by('-appointment_date', '-start_time') if patient else Appointment.objects.none()
    return render(request, 'dashboard/patient_dashboard.html', {'patient': patient, 'upcoming': upcoming[:5], 'history': history[:5]})


@login_required
def patient_profile(request):
    patient = Patient.objects.filter(user=request.user).first()
    if not patient:
        patient = Patient.objects.create(user=request.user, patient_id=f'P{request.user.id:04d}')
    if request.method == 'POST':
        form = PatientProfileForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            return redirect('patient_profile')
    else:
        form = PatientProfileForm(instance=patient)
    return render(request, 'dashboard/patient_profile.html', {'form': form, 'patient': patient})


@login_required
def patient_history(request):
    from datetime import datetime
    from django.db.models import Q
    patient = Patient.objects.filter(user=request.user).first()
    q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    appointments = Appointment.objects.filter(patient=patient).order_by('-appointment_date', '-start_time') if patient else Appointment.objects.none()
    if q:
        appointments = appointments.filter(
            Q(appointment_id__icontains=q) |
            Q(dentist__user__first_name__icontains=q) |
            Q(dentist__user__last_name__icontains=q) |
            Q(service__name__icontains=q) |
            Q(status__icontains=q)
        )
    if status_filter:
        appointments = appointments.filter(status=status_filter)
    if date_from:
        try:
            appointments = appointments.filter(appointment_date__gte=datetime.strptime(date_from, '%Y-%m-%d').date())
        except ValueError:
            pass
    if date_to:
        try:
            appointments = appointments.filter(appointment_date__lte=datetime.strptime(date_to, '%Y-%m-%d').date())
        except ValueError:
            pass
    status_choices = ['Pending', 'Confirmed', 'Checked-In', 'Completed', 'Cancelled', 'Rescheduled', 'No-Show']
    return render(request, 'dashboard/patient_history.html', {
        'appointments': appointments,
        'q': q,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'status_choices': status_choices,
    })

