from django import forms

from accounts.models import User
from dentists.models import Dentist


class UserCreateForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    role = forms.ChoiceField(choices=[('patient', 'Patient'), ('staff', 'Staff'), ('dentist', 'Dentist'), ('admin', 'Admin')])

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'phone', 'role', 'password')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if user.role == 'dentist':
            user.account_status = 'pending'
            user.is_active = False
        else:
            user.account_status = 'approved'
            user.is_active = True
        if commit:
            user.save()
        return user


class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'phone', 'role', 'is_active', 'account_status')


class DentistEditForm(forms.ModelForm):
    class Meta:
        model = Dentist
        fields = ('specialization', 'license_number', 'phone', 'biography', 'years_of_experience', 'active')
