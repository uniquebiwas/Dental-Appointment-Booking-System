from django import forms

from .models import DentistAvailability


class DentistAvailabilityForm(forms.ModelForm):
    apply_to_whole_week = forms.BooleanField(required=False, initial=False, label='Apply to all weekdays')

    class Meta:
        model = DentistAvailability
        fields = ('day_of_week', 'start_time', 'end_time', 'break_start', 'break_end', 'active')
        widgets = {
            'day_of_week': forms.Select(attrs={'class': 'form-select'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'break_start': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'break_end': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        break_start = cleaned_data.get('break_start')
        break_end = cleaned_data.get('break_end')

        if start_time and end_time and start_time >= end_time:
            raise forms.ValidationError('Working start time must be before end time.')
        if break_start and break_end:
            if break_start >= break_end:
                raise forms.ValidationError('Break start must come before break end.')
            if start_time and end_time and (break_start <= start_time or break_end >= end_time):
                raise forms.ValidationError('Break must fall within the working schedule.')

        return cleaned_data
