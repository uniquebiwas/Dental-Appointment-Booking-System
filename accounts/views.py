from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .forms import RegistrationForm
from patients.models import Patient


class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        if user.is_admin():
            return reverse_lazy('admin_dashboard')
        if user.is_dentist_approved():
            return reverse_lazy('dentist_dashboard')
        if user.is_staff_role():
            return reverse_lazy('staff_dashboard')
        return reverse_lazy('patient_dashboard')


def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            if user.role == 'dentist':
                messages.success(request, 'Dentist application submitted successfully. Your account is pending approval.')
            else:
                messages.success(request, 'Account created successfully. Please log in.')
            return render(request, 'registration/register.html', {'form': RegistrationForm()})
    else:
        form = RegistrationForm()
    return render(request, 'registration/register.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('home')
