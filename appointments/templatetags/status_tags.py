from django import template

register = template.Library()

STATUS_CLASS_MAP = {
    'Pending': 'pill-warning',
    'Confirmed': 'pill-success',
    'Checked-In': 'pill-primary',
    'Completed': 'pill-success',
    'Cancelled': 'pill-danger',
    'Rescheduled': 'pill-info',
    'No-Show': 'pill-secondary',
}

@register.filter
def status_badge_class(status):
    return STATUS_CLASS_MAP.get(status, 'pill-secondary')
