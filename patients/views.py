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
    patient = Patient.objects.filter(user=request.user).first()
    appointments = Appointment.objects.filter(patient=patient).order_by('-appointment_date', '-start_time') if patient else Appointment.objects.none()
    return render(request, 'dashboard/patient_history.html', {'appointments': appointments})
