import re
from decimal import Decimal

from django import template
from django.utils import timezone
from django.utils.html import escape, urlize
from django.utils.safestring import mark_safe
from django.utils.timesince import timesince, timeuntil

from apps.core.icons import icon_svg
from apps.core.models import TONE_DOT

register = template.Library()


@register.simple_tag
def icon(name, css="size-5", stroke="2"):
    """{% icon "users" "size-4 text-brand-500" %}"""
    return icon_svg(name, css, stroke)


def _group(value) -> str:
    try:
        number = int(round(float(value or 0)))
    except (TypeError, ValueError):
        return str(value)
    sign = "−" if number < 0 else ""
    return sign + f"{abs(number):,}".replace(",", " ")


@register.filter
def num(value):
    """1250000 → «1 250 000»"""
    return _group(value)


@register.filter
def money(value, currency="UZS"):
    """{{ amount|money:obj.currency }} → «1 250 000 so'm» yoki «$1 200»"""
    if currency == "USD":
        try:
            v = Decimal(value or 0)
        except (ArithmeticError, TypeError, ValueError):
            return value
        text = f"{abs(v):,.2f}".rstrip("0").rstrip(".").replace(",", " ")
        return mark_safe(f"{'−' if v < 0 else ''}${text}")
    return mark_safe(f"{_group(value)} so'm")


@register.filter
def totals(mapping):
    """{"UZS": 1000, "USD": 20} → «1 000 so'm · $20»"""
    parts = [money(v, c) for c, v in (mapping or {}).items() if v]
    return mark_safe(" · ".join(parts) if parts else "0 so'm")


@register.simple_tag(takes_context=True)
def active(context, key, css="is-active"):
    return css if context.get("nav_active") == key else ""


@register.filter
def ago(value):
    if not value:
        return ""
    return f"{timesince(value, depth=1)} oldin"


@register.filter
def left(value):
    if not value:
        return ""
    return timeuntil(value, depth=1)


@register.filter
def days_left(value):
    """Sana bugundan necha kun keyin (manfiy — o'tib ketgan)."""
    if not value:
        return None
    if hasattr(value, "date"):
        value = timezone.localtime(value).date()
    return (value - timezone.localdate()).days


@register.filter
def due_badge(value):
    """Muddat uchun badge klassi: o'tgan — qizil, 3 kun ichida — sariq."""
    d = days_left(value)
    if d is None:
        return "badge-neutral"
    if d < 0:
        return "badge-danger"
    if d <= 3:
        return "badge-warning"
    return "badge-neutral"


@register.filter
def due_label(value):
    d = days_left(value)
    if d is None:
        return ""
    if d == 0:
        return "Bugun"
    if d == 1:
        return "Ertaga"
    if d == -1:
        return "Kecha"
    if d < 0:
        return f"{-d} kun o'tdi"
    return f"{d} kundan keyin"


@register.filter
def dot(tone):
    return TONE_DOT.get(tone, "bg-ink-3")


@register.filter
def get_item(mapping, key):
    return mapping.get(key) if mapping else None


@register.filter
def pct(part, whole):
    try:
        return max(0, min(100, round(float(part) * 100 / float(whole))))
    except (TypeError, ValueError, ZeroDivisionError):
        return 0


@register.filter
def hours(value):
    """1.5 → «1 soat 30 daq»"""
    try:
        minutes = int(round(float(value or 0) * 60))
    except (TypeError, ValueError):
        return value
    h, m = divmod(minutes, 60)
    if h and m:
        return f"{h} soat {m} daq"
    if h:
        return f"{h} soat"
    return f"{m} daq"


@register.filter
def initials(text):
    words = [w for w in re.split(r"\s+", str(text or "").strip()) if w]
    return "".join(w[0] for w in words[:2]).upper() or "?"


@register.filter
def linkify(text):
    """Matndagi havolalarni bosiladigan qiladi (XSS'dan himoyalangan)."""
    return mark_safe(urlize(escape(text or ""), nofollow=True))
