from datetime import date

from django.shortcuts import get_object_or_404, render

from bookings.services import free_rooms, nights_between

from .models import RoomType


def _parse_date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def room_list(request):
    check_in = _parse_date(request.GET.get("check_in"))
    check_out = _parse_date(request.GET.get("check_out"))
    types = list(RoomType.objects.filter(is_active=True).prefetch_related("rooms"))
    has_dates = bool(check_in and check_out and check_out > check_in)
    for rt in types:
        rt.free_count = free_rooms(rt, check_in, check_out).count() if has_dates else None
    return render(request, "public/rooms.html", {
        "room_types": types, "check_in": check_in, "check_out": check_out, "has_dates": has_dates,
    })


def room_detail(request, slug):
    rt = get_object_or_404(RoomType, slug=slug, is_active=True)
    check_in = _parse_date(request.GET.get("check_in"))
    check_out = _parse_date(request.GET.get("check_out"))
    availability = None
    if check_in and check_out and check_out > check_in:
        nights = nights_between(check_in, check_out)
        availability = {
            "free": free_rooms(rt, check_in, check_out).count(),
            "nights": nights,
            "total": rt.price_per_night * nights,
        }
    return render(request, "public/room_detail.html", {
        "rt": rt, "check_in": check_in, "check_out": check_out, "availability": availability,
        "total_rooms": rt.rooms.exclude(status="maintenance").count(),
    })
