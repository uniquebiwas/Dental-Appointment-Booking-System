from django.urls import path
from .views import services_list

urlpatterns = [
    path('', services_list, name='services'),
]
