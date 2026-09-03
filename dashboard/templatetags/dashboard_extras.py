from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def querystring(context, **kwargs):
    params = context["request"].GET.copy()
    for key, value in kwargs.items():
        if value in (None, ""):
            params.pop(key, None)
        else:
            params[key] = value
    return params.urlencode()


@register.filter(name="currency")
def currency(value, symbol="UZS"):
    """
    Formats 3100000 -> 3,100,000 UZS (or 3 100 000 UZS)
    """
    if value is None or value == "":
        return f"0 {symbol}".strip()
    try:
        val = float(value)
        # Format with thousand space separator
        formatted = f"{val:,.0f}".replace(",", " ")
        return f"{formatted} {symbol}".strip()
    except (ValueError, TypeError):
        return f"{value} {symbol}".strip()


@register.filter(name="compact_num")
def compact_num(value, symbol="UZS"):
    """
    Formats 3100000 -> 3.1M UZS, 300000 -> 300K UZS
    """
    if value is None or value == "":
        return f"0 {symbol}".strip()
    try:
        val = abs(float(value))
        sign = "-" if float(value) < 0 else ""
        if val >= 1_000_000_000:
            formatted = f"{sign}{val / 1_000_000_000:.1f}B".replace(".0B", "B")
        elif val >= 1_000_000:
            formatted = f"{sign}{val / 1_000_000:.1f}M".replace(".0M", "M")
        elif val >= 1_000:
            formatted = f"{sign}{val / 1_000:.1f}K".replace(".0K", "K")
        else:
            formatted = f"{sign}{val:.0f}"
        return f"{formatted} {symbol}".strip()
    except (ValueError, TypeError):
        return f"{value} {symbol}".strip()


@register.filter(name="get_dict_item")
def get_dict_item(dictionary, key):
    if isinstance(dictionary, dict):
        return dictionary.get(key, 0)
    return 0


