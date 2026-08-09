from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = (
        ('patient', 'Patient'),
        ('staff', 'Staff'),
        ('dentist', 'Dentist'),
        ('admin', 'Admin'),
    )
    ACCOUNT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='patient')
    phone = models.CharField(max_length=20, blank=True)
    account_status = models.CharField(max_length=20, choices=ACCOUNT_STATUS_CHOICES, default='approved')

    def is_patient(self):
        return self.role == 'patient'

    def is_staff_role(self):
        return self.role in {'staff', 'admin'}

    def is_dentist(self):
        return self.role == 'dentist'

    def is_admin(self):
        return self.role == 'admin'

    def is_dentist_approved(self):
        return self.is_dentist() and self.is_active and self.account_status == 'approved'

    def status_label(self):
        if not self.is_active:
            return 'Inactive'
        if self.role == 'dentist':
            return self.get_account_status_display()
        return 'Active'

    def __str__(self):
        return self.get_full_name() or self.username
