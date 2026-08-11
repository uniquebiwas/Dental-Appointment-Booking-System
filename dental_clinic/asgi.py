"""
ASGI config for dental_clinic project – upgraded to Django Channels.

Handles both standard HTTP and WebSocket connections.
"""

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dental_clinic.settings')

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from dental_clinic.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
