"""Booking business logic: availability, price quotes and safe booking creation."""
from decimal import Decimal

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

from rooms.models import Room

from .models import Booking, Customer


class NoAvailability(Exception):
    pass


def nights_between(check_in, check_out):
    return max((check_out - check_in).days, 0)


def free_rooms(room_type, check_in, check_out, exclude_booking=None):
    """Rooms of this type that are in service and have no active booking overlapping the dates."""
    busy = Booking.objects.overlapping(check_in, check_out)
    if exclude_booking is not None and exclude_booking.pk:
        busy = busy.exclude(pk=exclude_booking.pk)
    return (Room.objects.filter(room_type=room_type, status=Room.AVAILABLE)
            .exclude(pk__in=busy.values("room_id")).order_by("number"))


def quote(room_type, check_in, check_out):
    nights = nights_between(check_in, check_out)
    return {
        "nights": nights,
        "price_per_night": room_type.price_per_night,
        "total": room_type.price_per_night * nights,
        "available": free_rooms(room_type, check_in, check_out).count(),
    }


@transaction.atomic
def create_public_booking(*, full_name, phone, email, room_type, check_in, check_out, guests, special_requests=""):
    """Pick a free room and create a Pending booking.

    Rooms of the type are locked (SELECT ... FOR UPDATE on PostgreSQL) inside one transaction
    and overlaps are re-checked, so two visitors cannot get the same room for overlapping dates."""
    rooms = list(Room.objects.select_for_update().filter(
        room_type=room_type, status=Room.AVAILABLE).order_by("number"))
    busy_ids = set(Booking.objects.overlapping(check_in, check_out)
                   .filter(room__in=rooms).values_list("room_id", flat=True))
    chosen = next((r for r in rooms if r.pk not in busy_ids), None)
    if chosen is None:
        raise NoAvailability("No room of this type is free for the selected dates.")

    customer = Customer.objects.filter(phone=phone).first()
    if customer is None:
        customer = Customer.objects.create(full_name=full_name, phone=phone, email=email)
    else:
        if not customer.email and email:
            customer.email = email
            customer.save(update_fields=["email"])

    booking = Booking(customer=customer, room=chosen, check_in=check_in, check_out=check_out,
                      guests=guests, special_requests=special_requests, source="online",
                      status=Booking.PENDING)
    booking.full_clean(exclude=["reference", "total_price", "created_by"])
    booking.save()
    return booking


def send_booking_email(booking, hotel_name):
    if not booking.customer.email:
        return
    body = (
        f"Dear {booking.customer.full_name},\n\n"
        f"Thank you for booking with {hotel_name}.\n\n"
        f"Reference: {booking.reference}\n"
        f"Room type: {booking.room.room_type.name_en}\n"
        f"Check-in: {booking.check_in:%A %d %B %Y}\n"
        f"Check-out: {booking.check_out:%A %d %B %Y}\n"
        f"Guests: {booking.guests}\n"
        f"Total: {booking.total_price}\n"
        f"Status: {booking.get_status_display()} (the hotel will confirm your reservation)\n\n"
        f"Keep your reference. You need it with your phone number to check your booking online.\n"
    )
    try:
        send_mail(f"Your booking {booking.reference} – {hotel_name}", body,
                  settings.DEFAULT_FROM_EMAIL, [booking.customer.email], fail_silently=True)
    except Exception:
        pass
