from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import User
from appointments.models import Appointment, AppointmentHistory
from dentists.models import Dentist
from patients.models import Patient
from reminders.models import Notification
from services.models import DentalService
from .forms import DentistEditForm, UserCreateForm, UserEditForm
from django.http import JsonResponse
import logging


def home(request):
    services = DentalService.objects.filter(active=True)[:6]
    dentists = Dentist.objects.filter(active=True)
    testimonials = [
        {
            'quote': 'The booking experience was effortless and the reminder system kept everything on track.',
            'author': 'Maya R. (Demo)',
            'rating': 5,
        },
        {
            'quote': 'The dashboard made it easier for our clinic to manage appointments and patient communication.',
            'author': 'Dr. N. Patel (Demo)',
            'rating': 4,
        },
        {
            'quote': 'Our patients love the clarity of appointment reminders and the care team stays informed.',
            'author': 'Sofia L. (Demo)',
            'rating': 5,
        },
    ]
    return render(request, 'home.html', {
        'services': services,
        'dentists': dentists,
        'testimonials': testimonials,
    })


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
    q = request.GET.get('q', '').strip()
    queryset = User.objects.all().order_by('-date_joined')
    if q:
        queryset = queryset.filter(
            Q(username__icontains=q) |
            Q(email__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(role__icontains=q)
        )
    if tab == 'pending':
        queryset = queryset.filter(is_active=False)
    elif tab == 'active':
        queryset = queryset.filter(is_active=True)
    elif tab == 'inactive':
        queryset = queryset.filter(is_active=False)
    elif tab == 'pending_dentists':
        queryset = queryset.filter(role='dentist', account_status='pending')

    users = list(queryset)
    dentist_profiles = Dentist.objects.filter(user__in=users)
    dentist_map = {dentist.user_id: dentist for dentist in dentist_profiles}
    for user in users:
        user.dentist_profile = dentist_map.get(user.pk)

    context = {'users': users, 'tab': tab, 'q': q}
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

    dentist = Dentist.objects.filter(pk=pk).first()
    if not dentist:
        dentist_user = User.objects.filter(pk=pk, role='dentist').first()
        if dentist_user:
            dentist = Dentist.objects.filter(user=dentist_user).first()
            if not dentist:
                dentist = Dentist.objects.create(
                    user=dentist_user,
                    dentist_id=f'DNT-{dentist_user.pk:04d}',
                    specialization='General Dentistry',
                    license_number=f'LIC-{dentist_user.pk:06d}',
                    phone=dentist_user.phone or '',
                    active=True,
                )

    if not dentist:
        return render(request, 'dashboard/access_denied.html')

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
    Dentist.objects.get_or_create(
        user=user,
        defaults={
            'dentist_id': f'DNT-{user.pk:04d}',
            'specialization': 'General Dentistry',
            'license_number': f'LIC-{user.pk:06d}',
            'phone': user.phone or '',
            'active': True,
        }
    )
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
def change_password(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    for field in form.fields.values():
        field.widget.attrs.setdefault('class', 'form-control')
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, 'Your password was changed successfully.')
        return redirect('change_password')
    return render(request, 'dashboard/change_password.html', {'form': form})


@login_required
def notifications_view(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    unread_count = notifications.filter(is_read=False).count()
    return render(request, 'dashboard/notifications.html', {
        'notifications': notifications,
        'unread_count': unread_count,
    })


@login_required
def mark_all_notifications_read(request):
    if request.method == 'POST':
        notif_qs = Notification.objects.filter(user=request.user, is_read=False)
        updated = notif_qs.update(is_read=True)
        logging.info(f"User {request.user.pk} marked all notifications as read ({updated} updated)")
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'unread_count': 0})
        return redirect('notifications')
    return JsonResponse({'success': False}, status=405)


@login_required
def mark_notification_read(request, pk):
    if request.method == 'POST':
        notif = get_object_or_404(Notification, pk=pk, user=request.user)
        notif.is_read = True
        notif.save()
        unread = Notification.objects.filter(user=request.user, is_read=False).count()
        logging.info(f"User {request.user.pk} marked notification {pk} as read")
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'unread_count': unread})
        return redirect('notifications')
    return JsonResponse({'success': False}, status=405)
