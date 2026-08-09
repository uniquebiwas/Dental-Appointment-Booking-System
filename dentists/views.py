from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from appointments.models import Appointment
from dentists.forms import DentistAvailabilityForm
from dentists.models import Dentist, DentistAvailability


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
    assigned_appointments = Appointment.objects.filter(dentist=dentist).order_by('-appointment_date', '-start_time')[:10]
    completed = Appointment.objects.filter(dentist=dentist, status='Completed').count()
    pending = Appointment.objects.filter(dentist=dentist, status='Pending').count()
    return render(request, 'dashboard/dentist_dashboard.html', {
        'dentist': dentist,
        'today': today[:10],
        'upcoming': upcoming[:10],
        'assigned_appointments': assigned_appointments,
        'completed': completed,
        'pending': pending,
    })


@login_required
def dentist_profile(request):
    if not request.user.is_dentist_approved():
        messages.error(request, 'Your dentist account is pending approval or inactive.')
        return redirect('home')
    dentist = Dentist.objects.filter(user=request.user).first()
    return render(request, 'dashboard/dentist_profile.html', {'dentist': dentist})


@login_required
def dentist_availability(request):
    if not request.user.is_dentist_approved():
        messages.error(request, 'Your dentist account is pending approval or inactive.')
        return redirect('home')
    dentist = Dentist.objects.filter(user=request.user).first()
    if not dentist:
        messages.error(request, 'Dentist profile not found.')
        return redirect('home')
    availabilities = DentistAvailability.objects.filter(dentist=dentist).order_by('day_of_week', 'start_time')
    return render(request, 'dashboard/dentist_availability.html', {'availabilities': availabilities})


@login_required
def dentist_add_availability(request):
    if not request.user.is_dentist_approved():
        messages.error(request, 'Your dentist account is pending approval or inactive.')
        return redirect('home')
    dentist = Dentist.objects.filter(user=request.user).first()
    if not dentist:
        messages.error(request, 'Dentist profile not found.')
        return redirect('home')
    form = DentistAvailabilityForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        apply_to_whole_week = form.cleaned_data.get('apply_to_whole_week', False)
        availability = form.save(commit=False)
        availability.dentist = dentist
        if apply_to_whole_week:
            availability.save()
            for day in range(1, 8):
                if day == availability.day_of_week:
                    continue
                DentistAvailability.objects.create(
                    dentist=dentist,
                    day_of_week=day,
                    start_time=availability.start_time,
                    end_time=availability.end_time,
                    break_start=availability.break_start,
                    break_end=availability.break_end,
                    active=availability.active,
                )
        else:
            availability.save()
        messages.success(request, 'Availability slot added successfully.')
        return redirect('dentist_availability')
    return render(request, 'dashboard/dentist_availability_form.html', {'form': form, 'title': 'Add Availability'})


@login_required
def dentist_edit_availability(request, pk):
    if not request.user.is_dentist_approved():
        messages.error(request, 'Your dentist account is pending approval or inactive.')
        return redirect('home')
    availability = get_object_or_404(DentistAvailability, pk=pk, dentist__user=request.user)
    form = DentistAvailabilityForm(request.POST or None, instance=availability)
    form.fields.pop('apply_to_whole_week', None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Availability slot updated successfully.')
        return redirect('dentist_availability')
    return render(request, 'dashboard/dentist_availability_form.html', {'form': form, 'title': 'Edit Availability'})


@login_required
def dentist_delete_availability(request, pk):
    if not request.user.is_dentist_approved():
        messages.error(request, 'Your dentist account is pending approval or inactive.')
        return redirect('home')
    availability = get_object_or_404(DentistAvailability, pk=pk, dentist__user=request.user)
    if request.method == 'POST':
        availability.delete()
        messages.success(request, 'Availability slot deleted successfully.')
        return redirect('dentist_availability')
    return render(request, 'dashboard/delete_confirm.html', {
        'title': 'Delete availability slot',
        'back_url': 'dentist_availability',
    })
