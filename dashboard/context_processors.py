from django.core.cache import cache
from django.utils import timezone


def alerts_count(request):
    if not request.user.is_authenticated:
        return {}
    from .views import _collect_alerts

    cache_key = f"nav-alerts-count:{timezone.localdate().isoformat()}"
    count = cache.get(cache_key)
    if count is None:
        count = len(_collect_alerts())
        cache.set(cache_key, count, 15)
    return {"nav_alerts_count": count}
