from django.urls import path
from .views import (
    dentist_dashboard,
    dentist_profile,
    dentist_availability,
    dentist_add_availability,
    dentist_edit_availability,
    dentist_delete_availability,
)

urlpatterns = [
    path('dashboard/', dentist_dashboard, name='dentist_dashboard'),
    path('profile/', dentist_profile, name='dentist_profile'),
    path('availability/', dentist_availability, name='dentist_availability'),
    path('availability/add/', dentist_add_availability, name='dentist_add_availability'),
    path('availability/<int:pk>/edit/', dentist_edit_availability, name='dentist_edit_availability'),
    path('availability/<int:pk>/delete/', dentist_delete_availability, name='dentist_delete_availability'),
]
