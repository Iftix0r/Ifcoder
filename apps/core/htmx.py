import json


def add_triggers(response, events: dict):
    """HTMX javobiga client-side hodisalar qo'shadi (HX-Trigger header)."""
    triggers = json.loads(response.headers.get("HX-Trigger") or "{}")
    triggers.update(events)
    response.headers["HX-Trigger"] = json.dumps(triggers)
    return response


def trigger_toast(response, message: str, level: str = "success"):
    return add_triggers(response, {"toast": {"message": str(message), "level": level}})
