from django.test import TestCase
from django.urls import reverse

from .models import User


class DentistApprovalTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin', password='secret123', role='admin', email='admin@example.com')
        self.admin.is_active = True
        self.admin.save()

    def test_dentist_registration_is_pending_and_inactive(self):
        response = self.client.post(reverse('register'), {
            'username': 'dentist1',
            'email': 'dentist1@example.com',
            'first_name': 'Dr',
            'last_name': 'Test',
            'phone': '123456789',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
            'account_type': 'dentist',
        })
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(username='dentist1')
        self.assertEqual(user.role, 'dentist')
        self.assertEqual(user.account_status, 'pending')
        self.assertFalse(user.is_active)

    def test_pending_dentist_cannot_access_dashboard(self):
        user = User.objects.create_user(username='dentist2', password='secret123', role='dentist', email='dentist2@example.com')
        user.account_status = 'pending'
        user.is_active = False
        user.save()
        self.client.force_login(user)
        response = self.client.get(reverse('dentist_dashboard'))
        self.assertNotEqual(response.status_code, 200)
