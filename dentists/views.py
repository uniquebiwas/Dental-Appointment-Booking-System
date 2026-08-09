from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from appointments.models import Appointment
from patients.models import Patient
from .models import Dentist


@login_required
def dentist_dashboard(request):
    if not request.user.is_dentist_approved():
        messages.error(request, 'Your dentist account is pending approval or inactive.')
        return redirect('home')
    dentist = Dentist.objects.filter(user=request.user).first()
    if not dentist:
        messages.error(request, 'Dentist profile not found.')
        return redirect('home')
    today = Appointment.objects.filter(dentist=dentist, appointment_date=timezone.localdate()).order_by('start_time')
    upcoming = Appointment.objects.filter(dentist=dentist, status__in=['Pending', 'Confirmed']).order_by('appointment_date', 'start_time')
    completed = Appointment.objects.filter(dentist=dentist, status='Completed').count()
    pending = Appointment.objects.filter(dentist=dentist, status='Pending').count()
    return render(request, 'dashboard/dentist_dashboard.html', {'dentist': dentist, 'today': today[:10], 'upcoming': upcoming[:10], 'completed': completed, 'pending': pending})


@login_required
def dentist_profile(request):
    if not request.user.is_dentist_approved():
        messages.error(request, 'Your dentist account is pending approval or inactive.')
        return redirect('home')
    dentist = Dentist.objects.filter(user=request.user).first()
    return render(request, 'dashboard/dentist_profile.html', {'dentist': dentist})
