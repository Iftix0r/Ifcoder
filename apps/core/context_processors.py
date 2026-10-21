from django.urls import NoReverseMatch

from .icons import icon_svg
from .navigation import NAV_SECTIONS


def _palette(sections):
    return [
        {"label": item.label, "section": title or "Umumiy", "href": item.href, "icon": icon_svg(item.icon, "size-4")}
        for title, items in sections
        for item in items
    ]


def app_context(request):
    user = getattr(request, "user", None)
    if not (user and user.is_authenticated) or request.path.startswith("/admin/"):
        return {}
    from apps.planner.services import running_entry

    try:
        return {
            "running_timer": running_entry(),
            "nav_sections": NAV_SECTIONS,
            "mobile_nav": [i for _, items in NAV_SECTIONS for i in items if i.mobile][:4],
            "palette_items": _palette(NAV_SECTIONS),
        }
    except NoReverseMatch:
        return {}
