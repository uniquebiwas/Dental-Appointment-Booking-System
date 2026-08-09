from django.shortcuts import render

from .models import DentalService


def services_list(request):
    services = DentalService.objects.filter(active=True)
    return render(request, 'dashboard/services.html', {'services': services})
