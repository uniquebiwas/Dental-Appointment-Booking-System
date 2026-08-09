from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import Reminder


@login_required
def reminder_list(request):
    reminders = Reminder.objects.all().order_by('-created_at')
    return render(request, 'dashboard/reminders.html', {'reminders': reminders})
