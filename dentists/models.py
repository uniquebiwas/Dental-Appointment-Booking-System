from django.conf import settings
from django.db import models


class Dentist(models.Model):
    dentist_id = models.CharField(max_length=20, unique=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    specialization = models.CharField(max_length=100)
    license_number = models.CharField(max_length=50, unique=True)
    phone = models.CharField(max_length=20, blank=True)
    biography = models.TextField(blank=True)
    years_of_experience = models.PositiveIntegerField(default=0)
    profile_photo = models.CharField(max_length=200, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Dr. {self.user.get_full_name() or self.user.username}"


class DentistAvailability(models.Model):
    DAY_CHOICES = [(i, day) for i, day in enumerate(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'], start=1)]

    dentist = models.ForeignKey(Dentist, related_name='availabilities', on_delete=models.CASCADE)
    day_of_week = models.PositiveIntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    break_start = models.TimeField(blank=True, null=True)
    break_end = models.TimeField(blank=True, null=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.dentist} - {self.get_day_of_week_display()}"
