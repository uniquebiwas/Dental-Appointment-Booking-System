from django import forms
from .models import Patient


class PatientProfileForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = ['patient_id', 'date_of_birth', 'gender', 'phone', 'address', 'emergency_contact', 'emergency_contact_phone', 'medical_notes', 'allergies']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }
