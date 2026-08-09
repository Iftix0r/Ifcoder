def alerts_count(request):
    if not request.user.is_authenticated:
        return {}
    from .views import _collect_alerts

    return {"nav_alerts_count": len(_collect_alerts())}
