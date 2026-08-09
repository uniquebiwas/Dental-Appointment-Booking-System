from django import forms
from .models import Patient


class PatientProfileForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = ['patient_id', 'date_of_birth', 'gender', 'phone', 'address', 'emergency_contact', 'emergency_contact_phone', 'medical_notes', 'allergies']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.Select):
                widget.attrs.setdefault('class', 'form-select')
            else:
                widget.attrs.setdefault('class', 'form-control')
