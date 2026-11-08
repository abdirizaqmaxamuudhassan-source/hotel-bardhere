from datetime import date

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET

from core.models import SiteSetting
from rooms.models import RoomType

from .forms import BookingLookupForm, PublicBookingForm
from .models import Booking
from .services import NoAvailability, create_public_booking, quote, send_booking_email


def booking_create(request):
    if request.method == "POST":
        form = PublicBookingForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            try:
                booking = create_public_booking(
                    full_name=data["full_name"], phone=data["phone"], email=data["email"],
                    room_type=data["room_type"], check_in=data["check_in"], check_out=data["check_out"],
                    guests=data["guests"], special_requests=data["special_requests"])
            except NoAvailability:
                form.add_error("room_type", "Sorry, the last room of this type was just booked. Please try other dates.")
            else:
                send_booking_email(booking, SiteSetting.load().hotel_name)
                # Remember which booking this browser created so the confirmation page can be shown.
                allowed = request.session.get("my_bookings", [])
                allowed.append(booking.reference)
                request.session["my_bookings"] = allowed[-10:]
                return redirect("bookings:confirmation", reference=booking.reference)
    else:
        initial = {k: request.GET.get(k) for k in ("check_in", "check_out", "guests", "room_type") if request.GET.get(k)}
        form = PublicBookingForm(initial=initial)
    return render(request, "public/booking.html", {"form": form})


def confirmation(request, reference):
    booking = get_object_or_404(Booking.objects.select_related("customer", "room__room_type"), reference=reference)
    if reference not in request.session.get("my_bookings", []):
        return redirect("bookings:status")  # others must verify with phone number
    return render(request, "public/booking_confirmation.html", {"booking": booking})


def booking_status(request):
    booking = None
    if request.method == "POST":
        form = BookingLookupForm(request.POST)
        if form.is_valid():
            ref = form.cleaned_data["reference"].strip().upper()
            digits = "".join(c for c in form.cleaned_data["phone"] if c.isdigit())
            candidate = Booking.objects.select_related("customer", "room__room_type").filter(reference=ref).first()
            if candidate and digits and "".join(c for c in candidate.customer.phone if c.isdigit()) == digits:
                booking = candidate
            else:
                form.add_error(None, "No booking matches that reference and phone number.")
    else:
        form = BookingLookupForm()
    return render(request, "public/booking_status.html", {"form": form, "booking": booking})


@require_GET
def quote_api(request):
    """Live price/availability used by the booking form. Same logic as the real booking."""
    try:
        rt = RoomType.objects.get(pk=int(request.GET.get("room_type", "")), is_active=True)
        ci = date.fromisoformat(request.GET.get("check_in", ""))
        co = date.fromisoformat(request.GET.get("check_out", ""))
    except (ValueError, RoomType.DoesNotExist):
        return JsonResponse({"ok": False})
    if co <= ci:
        return JsonResponse({"ok": False, "error": "dates"})
    q = quote(rt, ci, co)
    return JsonResponse({
        "ok": True, "nights": q["nights"], "price_per_night": str(q["price_per_night"]),
        "total": str(q["total"]), "available": q["available"], "capacity": rt.capacity,
    })
