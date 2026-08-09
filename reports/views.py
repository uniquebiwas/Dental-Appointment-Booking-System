from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from appointments.models import Appointment
from patients.models import Patient
from services.models import DentalService


@login_required
def reports_dashboard(request):
    appointments = Appointment.objects.select_related('patient', 'dentist', 'service').all()
    return render(request, 'dashboard/reports.html', {
        'appointments': appointments,
        'patient_count': Patient.objects.count(),
        'service_count': DentalService.objects.count(),
        'appointment_count': appointments.count(),
    })
