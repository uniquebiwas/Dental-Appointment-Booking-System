from django.urls import path
from .views import dentist_dashboard, dentist_profile

urlpatterns = [
    path('dashboard/', dentist_dashboard, name='dentist_dashboard'),
    path('profile/', dentist_profile, name='dentist_profile'),
]
