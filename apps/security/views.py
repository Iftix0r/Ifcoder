from django.conf import settings as conf
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core import telegram
from apps.vault.services import has_2fa

from . import services
from .forms import TrustedForm
from .models import Event, ScanState, TrustedIP

EVENT_LIMIT = 150


def home(request):
    kind = request.GET.get("kind", "")
    events = Event.objects.all()
    if kind in Event.Kind.values:
        events = events.filter(kind=kind)
    trusted = list(TrustedIP.objects.values_list("ip", flat=True))
    rows = list(events[:EVENT_LIMIT])
    for row in rows:
        row.trusted = any(row.ip.startswith(item) for item in trusted)
    current = services.key_hash(request.session.session_key) if request.session.session_key else ""
    return render(
        request,
        "security/home.html",
        {
            "nav_active": "security",
            "events": rows,
            "kinds": Event.Kind.choices,
            "kind": kind,
            "sessions": services.active_sessions(),
            "current_hash": current,
            "my_ip": services.client_ip(request),
            "trusted_rows": TrustedIP.objects.all(),
            "form": TrustedForm(),
            "has_2fa": has_2fa(request.user),
            "bot_ok": telegram.is_configured(),
            "scanned_at": ScanState.load().scanned_at,
            "log_set": bool(conf.SECURITY_ACCESS_LOG),
        },
    )


@require_POST
def trust(request):
    form = TrustedForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Ishonchli ro'yxatga qo'shildi.")
    else:
        messages.error(request, "Manzil noto'g'ri yoki ro'yxatda bor.")
    return redirect("security_home")


@require_POST
def untrust(request, pk):
    get_object_or_404(TrustedIP, pk=pk).delete()
    return redirect("security_home")


@require_POST
def kill(request):
    digest = request.POST.get("key", "")
    current = services.key_hash(request.session.session_key) if request.session.session_key else ""
    if digest == current:
        messages.error(request, "Joriy sessiyani bu yerdan yopib bo'lmaydi: chiqish tugmasidan foydalaning.")
    elif services.kill_session(digest, services.client_ip(request), request.user.get_username()):
        messages.success(request, "Sessiya yopildi.")
    return redirect("security_home")
