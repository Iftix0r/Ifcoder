from django.core.cache import cache
from django.utils import timezone


def alerts_count(request):
    if not request.user.is_authenticated:
        return {}
    from .views import _collect_alerts
    from tickets.models import Ticket

    cache_key = f"nav-alerts-count:{timezone.localdate().isoformat()}"
    count = cache.get(cache_key)
    if count is None:
        count = len(_collect_alerts())
        cache.set(cache_key, count, 15)

    open_tickets = Ticket.objects.filter(
        status__in=[Ticket.Status.OPEN, Ticket.Status.IN_PROGRESS]
    ).count()

    return {
        "nav_alerts_count": count,
        "nav_open_tickets_count": open_tickets,
    }
