from django.conf import settings
from django.db import models
from django.db.models import F, Q

from dentists.models import Dentist
from patients.models import Patient
from services.models import DentalService


class Appointment(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Checked-In', 'Checked-In'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
        ('Rescheduled', 'Rescheduled'),
        ('No-Show', 'No-Show'),
    )

    appointment_id = models.CharField(max_length=20, unique=True)
    patient = models.ForeignKey(Patient, related_name='appointments', on_delete=models.CASCADE)
    dentist = models.ForeignKey(Dentist, related_name='appointments', on_delete=models.CASCADE)
    service = models.ForeignKey(DentalService, related_name='appointments', on_delete=models.CASCADE)
    appointment_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    reason = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    cancellation_reason = models.TextField(blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(end_time__gt=F('start_time')), name='check_appointment_times'),
        ]

    def __str__(self):
        return f"{self.appointment_id} - {self.patient}"


class AppointmentHistory(models.Model):
    appointment = models.ForeignKey(Appointment, related_name='history', on_delete=models.CASCADE)
    previous_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.appointment} - {self.previous_status} -> {self.new_status}"


class PatientVisit(models.Model):
    patient = models.ForeignKey(Patient, related_name='visits', on_delete=models.CASCADE)
    appointment = models.ForeignKey(Appointment, related_name='patient_visits', on_delete=models.CASCADE)
    dentist = models.ForeignKey(Dentist, related_name='patient_visits', on_delete=models.CASCADE)
    diagnosis = models.TextField(blank=True)
    treatment = models.TextField(blank=True)
    prescription = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Visit for {self.patient}"
