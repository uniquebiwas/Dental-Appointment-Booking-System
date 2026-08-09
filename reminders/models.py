from django.conf import settings
from django.db import models

from appointments.models import Appointment


class Reminder(models.Model):
    REMINDER_TYPE_CHOICES = (
        ('24 Hours Before', '24 Hours Before'),
        ('2 Hours Before', '2 Hours Before'),
        ('Follow-Up', 'Follow-Up'),
    )
    CHANNEL_CHOICES = (
        ('Email', 'Email'),
        ('SMS', 'SMS'),
    )
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Sent', 'Sent'),
        ('Failed', 'Failed'),
    )

    appointment = models.ForeignKey(Appointment, related_name='reminders', on_delete=models.CASCADE)
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPE_CHOICES)
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    scheduled_for = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')
    message = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.reminder_type} for {self.appointment}"


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='notifications', on_delete=models.CASCADE)
    appointment = models.ForeignKey(Appointment, related_name='notifications_appt', null=True, blank=True, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, default='info')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
