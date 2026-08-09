from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import User
from appointments.models import Appointment, AppointmentHistory
from dentists.models import Dentist
from patients.models import Patient
from reminders.models import Notification
from services.models import DentalService
from .forms import DentistEditForm, UserCreateForm, UserEditForm


def home(request):
    services = DentalService.objects.filter(active=True)[:6]
    dentists = Dentist.objects.filter(active=True)[:6]
    return render(request, 'home.html', {'services': services, 'dentists': dentists})


@login_required
def admin_dashboard(request):
    if not request.user.is_admin():
        return render(request, 'dashboard/access_denied.html')
    appointments = Appointment.objects.select_related('patient', 'dentist', 'service').all()
    pending_dentists = User.objects.filter(role='dentist', account_status='pending').order_by('-date_joined')[:10]
    return render(request, 'dashboard/admin_dashboard.html', {
        'patient_count': Patient.objects.count(),
        'dentist_count': Dentist.objects.count(),
        'appointment_count': appointments.count(),
        'completed_count': appointments.filter(status='Completed').count(),
        'cancelled_count': appointments.filter(status='Cancelled').count(),
        'upcoming_count': appointments.filter(status__in=['Pending', 'Confirmed', 'Checked-In']).count(),
        'no_show_count': appointments.filter(status='No-Show').count(),
        'todays_appointments': appointments.filter(appointment_date=timezone.localdate()).order_by('start_time')[:10],
        'pending_appointments': appointments.filter(status='Pending').count(),
        'pending_dentists': pending_dentists,
        'appointments': appointments.order_by('-appointment_date')[:10],
        'activity': AppointmentHistory.objects.order_by('-timestamp')[:10],
    })


@login_required
def admin_users(request):
    if not request.user.is_admin():
        return render(request, 'dashboard/access_denied.html')
    tab = request.GET.get('tab', 'all')
    queryset = User.objects.all().order_by('-date_joined')
    if tab == 'pending':
        queryset = queryset.filter(is_active=False)
    elif tab == 'active':
        queryset = queryset.filter(is_active=True)
    elif tab == 'inactive':
        queryset = queryset.filter(is_active=False)
    elif tab == 'pending_dentists':
        queryset = queryset.filter(role='dentist', account_status='pending')
    context = {'users': queryset, 'tab': tab}
    return render(request, 'dashboard/admin_users.html', context)


@login_required
def admin_user_detail(request, pk):
    if not request.user.is_admin():
        return render(request, 'dashboard/access_denied.html')
    user = get_object_or_404(User, pk=pk)
    appointments = Appointment.objects.filter(patient__user=user).order_by('-appointment_date') if user.role == 'patient' else Appointment.objects.filter(dentist__user=user).order_by('-appointment_date')
    return render(request, 'dashboard/admin_user_detail.html', {'user': user, 'appointments': appointments})


@login_required
def admin_create_user(request):
    if not request.user.is_admin():
        return render(request, 'dashboard/access_denied.html')
    form = UserCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        messages.success(request, 'User created successfully.')
        return redirect('admin_users')
    return render(request, 'dashboard/admin_user_form.html', {'form': form, 'title': 'Create User'})


@login_required
def admin_edit_user(request, pk):
    if not request.user.is_admin():
        return render(request, 'dashboard/access_denied.html')
    user = get_object_or_404(User, pk=pk)
    form = UserEditForm(request.POST or None, instance=user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'User updated successfully.')
        return redirect('admin_users')
    return render(request, 'dashboard/admin_user_form.html', {'form': form, 'title': 'Edit User', 'user': user})


@login_required
def admin_edit_dentist(request, pk):
    if not request.user.is_admin():
        return render(request, 'dashboard/access_denied.html')
    dentist = get_object_or_404(Dentist, pk=pk)
    form = DentistEditForm(request.POST or None, instance=dentist)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Dentist profile updated successfully.')
        return redirect('admin_users')
    return render(request, 'dashboard/admin_dentist_form.html', {'form': form, 'dentist': dentist})


@login_required
def approve_dentist(request, pk):
    if not request.user.is_admin():
        return render(request, 'dashboard/access_denied.html')
    user = get_object_or_404(User, pk=pk)
    user.account_status = 'approved'
    user.is_active = True
    user.save()
    messages.success(request, 'Dentist approved successfully.')
    return redirect('admin_users')


@login_required
def reject_dentist(request, pk):
    if not request.user.is_admin():
        return render(request, 'dashboard/access_denied.html')
    user = get_object_or_404(User, pk=pk)
    user.account_status = 'rejected'
    user.is_active = False
    user.save()
    messages.warning(request, 'Dentist rejected.')
    return redirect('admin_users')


@login_required
def toggle_user_status(request, pk):
    if not request.user.is_admin():
        return render(request, 'dashboard/access_denied.html')
    user = get_object_or_404(User, pk=pk)
    user.is_active = not user.is_active
    if user.is_active:
        user.account_status = 'approved' if user.role == 'dentist' else user.account_status
    user.save()
    messages.success(request, 'User status updated.')
    return redirect('admin_users')


@login_required
def delete_user(request, pk):
    if not request.user.is_admin():
        return render(request, 'dashboard/access_denied.html')
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        user.delete()
        messages.success(request, 'User deleted successfully.')
        return redirect('admin_users')
    return render(request, 'dashboard/delete_confirm.html', {'user': user})


@login_required
def reset_password(request, pk):
    if not request.user.is_admin():
        return render(request, 'dashboard/access_denied.html')
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        new_password = request.POST.get('password') or 'Dental@2026'
        user.set_password(new_password)
        user.save()
        messages.success(request, 'Password reset successfully.')
        return redirect('admin_users')
    return render(request, 'dashboard/reset_password.html', {'user': user})


@login_required
def notifications_view(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'dashboard/notifications.html', {'notifications': notifications})
