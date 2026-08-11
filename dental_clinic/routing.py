from django.urls import re_path
from reminders.consumers import NotificationConsumer

websocket_urlpatterns = [
    re_path(r'^ws/notifications/(?P<user_pk>\d+)/$', NotificationConsumer.as_asgi()),
]
