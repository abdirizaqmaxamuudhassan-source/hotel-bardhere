from decimal import Decimal

from django import template

from core.i18n import SO

register = template.Library()


def _lang(context):
    request = context.get("request")
    return getattr(request, "LANG", "en")


@register.simple_tag(takes_context=True)
def t(context, text):
    """{% t "English text" %} -> Somali when the visitor chose Somali."""
    if _lang(context) == "so":
        return SO.get(text, text)
    return text


@register.simple_tag(takes_context=True)
def loc(context, obj, field):
    """{% loc room 'name' %} -> room.name_so (if Somali and filled) else room.name_en."""
    if obj is None:
        return ""
    if _lang(context) == "so":
        value = getattr(obj, f"{field}_so", "")
        if value:
            return value
    return getattr(obj, f"{field}_en", "")


@register.simple_tag(takes_context=True)
def loclines(context, obj, field):
    """Returns a list of non-empty lines from a localised multi-line field."""
    text = ""
    if _lang(context) == "so":
        text = getattr(obj, f"{field}_so", "")
    if not text:
        text = getattr(obj, f"{field}_en", "")
    return [line.strip() for line in text.splitlines() if line.strip()]


@register.simple_tag(takes_context=True)
def money(context, amount):
    site = context.get("site")
    symbol = site.currency_symbol if site else "$"
    try:
        value = Decimal(amount or 0)
    except Exception:
        value = Decimal(0)
    return f"{symbol}{value:,.2f}"


@register.filter
def getitem(mapping, key):
    try:
        return mapping.get(key)
    except AttributeError:
        return None
