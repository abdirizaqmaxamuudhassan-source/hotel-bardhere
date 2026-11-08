import secrets
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum
from django.utils import timezone

from rooms.models import Room

REF_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


class Customer(models.Model):
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30)
    email = models.EmailField(blank=True)
    id_number = models.CharField("ID / passport number", max_length=50, blank=True)
    address = models.CharField(max_length=250, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return f"{self.full_name} ({self.phone})"


class BookingQuerySet(models.QuerySet):
    def active(self):
        return self.filter(status__in=Booking.ACTIVE_STATUSES)

    def overlapping(self, check_in, check_out):
        """Active bookings whose stay overlaps [check_in, check_out).
        A guest leaving on the day another arrives is NOT an overlap."""
        return self.active().filter(check_in__lt=check_out, check_out__gt=check_in)


class Booking(models.Model):
    PENDING, CONFIRMED, CANCELLED = "pending", "confirmed", "cancelled"
    STATUS_CHOICES = [(PENDING, "Pending"), (CONFIRMED, "Confirmed"), (CANCELLED, "Cancelled")]
    ACTIVE_STATUSES = (PENDING, CONFIRMED)
    SOURCE_CHOICES = [("online", "Website"), ("walk_in", "Walk-in"), ("phone", "Phone / WhatsApp")]

    reference = models.CharField(max_length=12, unique=True, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="bookings")
    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="bookings")
    check_in = models.DateField()
    check_out = models.DateField()
    guests = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1)])
    price_per_night = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Leave empty to use the room type's current price.")
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default="online")
    special_requests = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="+", editable=False)

    objects = BookingQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["room", "check_in", "check_out"])]

    def __str__(self):
        return self.reference

    # ---- calculations
    @property
    def nights(self):
        if self.check_in and self.check_out:
            return max((self.check_out - self.check_in).days, 0)
        return 0

    @property
    def room_type(self):
        return self.room.room_type

    @property
    def amount_paid(self):
        total = self.payments.filter(status=Payment.COMPLETED).aggregate(s=Sum("amount"))["s"]
        return total or Decimal("0")

    @property
    def balance_due(self):
        return max(self.total_price - self.amount_paid, Decimal("0"))

    @property
    def payment_state(self):
        paid = self.amount_paid
        if paid <= 0:
            return "Unpaid"
        if paid >= self.total_price:
            return "Paid"
        return "Partial"

    # ---- validation (also runs in admin and staff forms)
    def clean(self):
        errors = {}
        if self.check_in and self.check_out and self.check_out <= self.check_in:
            errors["check_out"] = "Check-out must be after check-in."
        if self.room_id and self.guests and self.guests > self.room.room_type.capacity:
            errors["guests"] = f"This room holds at most {self.room.room_type.capacity} guests."
        if (self.status in self.ACTIVE_STATUSES and self.room_id and self.check_in and self.check_out
                and self.check_out > self.check_in):
            if self.room.status != Room.AVAILABLE:
                errors["room"] = "This room is under maintenance."
            clash = Booking.objects.overlapping(self.check_in, self.check_out).filter(
                room_id=self.room_id).exclude(pk=self.pk)
            if clash.exists():
                other = clash.first()
                errors["room"] = (f"Room {self.room.number} is already booked for these dates "
                                  f"({other.reference}: {other.check_in:%d %b} – {other.check_out:%d %b}).")
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.reference:
            while True:
                ref = "HB-" + "".join(secrets.choice(REF_ALPHABET) for _ in range(6))
                if not Booking.objects.filter(reference=ref).exists():
                    self.reference = ref
                    break
        if self.price_per_night is None and self.room_id:
            self.price_per_night = self.room.room_type.price_per_night
        self.total_price = (self.price_per_night or Decimal("0")) * self.nights
        super().save(*args, **kwargs)


class Payment(models.Model):
    CASH, MOBILE, EVC, ZAAD, EDAHAB = "cash", "mobile_money", "evc_plus", "zaad", "edahab"
    METHOD_CHOICES = [
        (CASH, "Cash"), (MOBILE, "Mobile Money"), (EVC, "EVC Plus"), (ZAAD, "ZAAD"), (EDAHAB, "eDahab"),
    ]
    PENDING, COMPLETED, FAILED, REFUNDED = "pending", "completed", "failed", "refunded"
    STATUS_CHOICES = [(PENDING, "Pending"), (COMPLETED, "Completed"), (FAILED, "Failed"), (REFUNDED, "Refunded")]

    booking = models.ForeignKey(Booking, on_delete=models.PROTECT, related_name="payments")
    method = models.CharField(max_length=15, choices=METHOD_CHOICES, default=CASH)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    transaction_reference = models.CharField(
        max_length=80, blank=True,
        help_text="Transaction ID from the customer's mobile money message. Entered by staff; not verified automatically.")
    payer_phone = models.CharField("Paying phone number", max_length=30, blank=True)
    paid_at = models.DateField(default=timezone.localdate)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=COMPLETED)
    notes = models.CharField(max_length=250, blank=True)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="+", editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-paid_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["method", "transaction_reference"],
                condition=~models.Q(transaction_reference=""),
                name="unique_payment_reference_per_method",
                violation_error_message="A payment with this method and transaction reference is already recorded."),
        ]

    def __str__(self):
        return f"{self.receipt_number} – {self.amount}"

    @property
    def receipt_number(self):
        return f"RC-{self.pk:06d}" if self.pk else "RC-NEW"

    def clean(self):
        if self.method != self.CASH and not (self.transaction_reference or "").strip():
            raise ValidationError({"transaction_reference": "Enter the transaction reference for mobile money payments."})
        if self.transaction_reference:
            self.transaction_reference = self.transaction_reference.strip()
