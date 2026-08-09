from django.urls import path
from .views import appointment_detail, appointment_history, book_appointment, cancel_appointment, reschedule_appointment, staff_dashboard

urlpatterns = [
    path('book/', book_appointment, name='book_appointment'),
    path('<int:pk>/', appointment_detail, name='appointment_detail'),
    path('history/', appointment_history, name='appointment_history'),
    path('<int:pk>/cancel/', cancel_appointment, name='cancel_appointment'),
    path('<int:pk>/reschedule/', reschedule_appointment, name='reschedule_appointment'),
    path('staff-dashboard/', staff_dashboard, name='staff_dashboard'),
]
