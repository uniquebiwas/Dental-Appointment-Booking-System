import json
from channels.generic.websocket import AsyncWebsocketConsumer


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer that delivers real-time notifications to the
    connected user.  Each user gets their own channel group:
    ``notifications_<user_pk>``.
    """

    async def connect(self):
        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            await self.close()
            return

        self.user_pk = str(user.pk)
        self.group_name = f"notifications_{self.user_pk}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name, self.channel_name
            )

    # Receive message from WebSocket (client → server — not used, but kept for completeness)
    async def receive(self, text_data=None, bytes_data=None):
        pass

    # ──────────────────────────────────────────────
    # Handler: called when the group receives a
    # message via channel_layer.group_send(...)
    # ──────────────────────────────────────────────
    async def send_notification(self, event):
        """Relay a notification to the WebSocket client."""
        await self.send(text_data=json.dumps({
            "title":   event.get("title", "Notification"),
            "message": event.get("message", ""),
            "type":    event.get("notification_type", "info"),
        }))
