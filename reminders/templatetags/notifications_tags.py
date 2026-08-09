from django import template
from reminders.models import Notification

register = template.Library()

@register.simple_tag(takes_context=True)
def unread_notifications_count(context):
    request = context.get('request')
    if not request or not request.user.is_authenticated:
        return 0
    return Notification.objects.filter(user=request.user, is_read=False).count()
