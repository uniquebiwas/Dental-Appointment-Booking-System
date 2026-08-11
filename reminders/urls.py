from django.urls import path
from .views import reminder_list, send_reminder_email

urlpatterns = [
    path('', reminder_list, name='reminders'),
    path('send/<int:pk>/', send_reminder_email, name='send_reminder_email'),
]
