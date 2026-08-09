from django.urls import path
from .views import (admin_create_user, admin_dashboard, admin_edit_dentist, admin_edit_user, admin_user_detail,
                    admin_users, approve_dentist, delete_user, home, notifications_view, reject_dentist,
                    reset_password, toggle_user_status)

urlpatterns = [
    path('', home, name='home'),
    path('dashboard/admin/', admin_dashboard, name='admin_dashboard'),
    path('dashboard/admin/users/', admin_users, name='admin_users'),
    path('dashboard/admin/users/create/', admin_create_user, name='admin_create_user'),
    path('dashboard/admin/users/<int:pk>/', admin_user_detail, name='admin_user_detail'),
    path('dashboard/admin/users/<int:pk>/edit/', admin_edit_user, name='admin_edit_user'),
    path('dashboard/admin/dentists/<int:pk>/edit/', admin_edit_dentist, name='admin_edit_dentist'),
    path('dashboard/admin/users/<int:pk>/approve/', approve_dentist, name='approve_dentist'),
    path('dashboard/admin/users/<int:pk>/reject/', reject_dentist, name='reject_dentist'),
    path('dashboard/admin/users/<int:pk>/toggle/', toggle_user_status, name='toggle_user_status'),
    path('dashboard/admin/users/<int:pk>/delete/', delete_user, name='delete_user'),
    path('dashboard/admin/users/<int:pk>/reset-password/', reset_password, name='reset_password'),
    path('notifications/', notifications_view, name='notifications'),
]
