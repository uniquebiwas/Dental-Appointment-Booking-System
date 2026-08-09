from django.urls import path
from .views import patient_dashboard, patient_profile, patient_history

urlpatterns = [
    path('dashboard/', patient_dashboard, name='patient_dashboard'),
    path('profile/', patient_profile, name='patient_profile'),
    path('history/', patient_history, name='patient_history'),
]
