from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(required=False)
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)
    account_type = forms.ChoiceField(choices=[('patient', 'Register as Patient'), ('dentist', 'Apply as Dentist')], required=True, widget=forms.RadioSelect)

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'phone', 'password1', 'password2', 'account_type')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.RadioSelect):
                widget.attrs.setdefault('class', 'form-check-input')
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault('class', 'form-select')
            else:
                widget.attrs.setdefault('class', 'form-control')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.phone = self.cleaned_data['phone']
        role = self.cleaned_data['account_type']
        user.role = role
        if role == 'dentist':
            user.account_status = 'pending'
            user.is_active = False
        else:
            user.account_status = 'approved'
            user.is_active = True
        if commit:
            user.save()
        return user
