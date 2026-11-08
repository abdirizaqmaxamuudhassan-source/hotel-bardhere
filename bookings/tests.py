from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from dashboard.models import Employee
from rooms.models import Room, RoomType

from .models import Booking, Customer, Payment
from .services import NoAvailability, create_public_booking, free_rooms


class BookingRulesTests(TestCase):
    def setUp(self):
        self.rt = RoomType.objects.create(name_en="Standard", description_en="x", price_per_night=40, capacity=2)
        self.room = Room.objects.create(number="101", room_type=self.rt)
        self.today = timezone.localdate()
        self.cust = Customer.objects.create(full_name="Test Guest", phone="+252611111111")

    def _book(self, start, end, status=Booking.CONFIRMED):
        b = Booking(customer=self.cust, room=self.room, check_in=self.today + timedelta(days=start),
                    check_out=self.today + timedelta(days=end), guests=1, status=status)
        b.full_clean(exclude=["reference", "total_price", "created_by"])
        b.save()
        return b

    def test_total_price_is_nights_times_rate(self):
        b = self._book(1, 4)
        self.assertEqual(b.nights, 3)
        self.assertEqual(b.total_price, 120)

    def test_overlap_is_rejected(self):
        self._book(1, 4)
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            self._book(3, 6)

    def test_same_day_turnover_is_allowed(self):
        self._book(1, 4)
        self._book(4, 6)  # guest leaves on the day the next one arrives

    def test_cancelled_booking_frees_the_room(self):
        b = self._book(1, 4)
        b.status = Booking.CANCELLED
        b.save()
        self._book(2, 3)

    def test_public_booking_never_double_books(self):
        kwargs = dict(full_name="A", phone="+252622222222", email="", room_type=self.rt,
                      check_in=self.today + timedelta(days=2), check_out=self.today + timedelta(days=4), guests=1)
        create_public_booking(**kwargs)
        with self.assertRaises(NoAvailability):
            create_public_booking(**kwargs)
        self.assertEqual(free_rooms(self.rt, kwargs["check_in"], kwargs["check_out"]).count(), 0)

    def test_public_booking_form_flow(self):
        resp = self.client.post(reverse("bookings:create"), {
            "full_name": "Form Guest", "phone": "+252 61 555 5555", "email": "",
            "check_in": (self.today + timedelta(days=5)).isoformat(),
            "check_out": (self.today + timedelta(days=7)).isoformat(),
            "guests": 2, "room_type": self.rt.pk, "special_requests": ""})
        self.assertEqual(resp.status_code, 302)
        booking = Booking.objects.get(customer__full_name="Form Guest")
        self.assertEqual(booking.status, Booking.PENDING)
        self.assertEqual(booking.total_price, 80)

    def test_mobile_money_requires_reference(self):
        b = self._book(1, 2)
        p = Payment(booking=b, method=Payment.EVC, amount=10)
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            p.full_clean(exclude=["received_by"])


class AccessTests(TestCase):
    def test_dashboard_requires_login(self):
        resp = self.client.get(reverse("dashboard:home"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("dashboard:login"), resp["Location"])

    def test_receptionist_cannot_open_employees(self):
        User = get_user_model()
        u = User.objects.create_user("rec", password="a-Long-pass-123")
        Employee.objects.create(user=u, full_name="Rec", role="receptionist")
        self.client.login(username="rec", password="a-Long-pass-123")
        self.assertEqual(self.client.get(reverse("dashboard:employee_list")).status_code, 403)
        self.assertEqual(self.client.get(reverse("dashboard:home")).status_code, 200)
