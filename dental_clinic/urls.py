from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path('accounts/', include('accounts.urls')),
    path('patients/', include('patients.urls')),
    path('dentists/', include('dentists.urls')),
    path('services/', include('services.urls')),
    path('appointments/', include('appointments.urls')),
    path('reminders/', include('reminders.urls')),
    path('reports/', include('reports.urls')),
]
