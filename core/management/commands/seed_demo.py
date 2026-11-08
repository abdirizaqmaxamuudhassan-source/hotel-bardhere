"""python manage.py seed_demo [--with-staff]

Creates starter content (room types, rooms, services, menu) so the site is not empty.
Everything can be edited or deleted from the dashboard afterwards. Safe to run twice."""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils.crypto import get_random_string

from core.models import MenuCategory, MenuItem, Service, SiteSetting
from dashboard.models import Employee
from rooms.models import Room, RoomType

ROOM_TYPES = [
    # name_en, name_so, price, capacity, bed, size, facilities_en, description_en, rooms
    ("Standard Room", "Qol caadi ah", 35, 2, "1 double bed", 18,
     "Free Wi-Fi\nAir conditioning\nPrivate bathroom\nTV\nHot water",
     "A clean, quiet room with everything needed for a comfortable stay.", ["101", "102", "103", "104"]),
    ("Deluxe Room", "Qol heersare ah", 55, 2, "1 king bed", 26,
     "Free Wi-Fi\nAir conditioning\nPrivate bathroom\nTV\nHot water\nWriting desk\nBalcony",
     "More space, a king bed and a writing desk for business travellers.", ["201", "202", "203"]),
    ("Family Room", "Qol qoys", 75, 4, "2 double beds", 34,
     "Free Wi-Fi\nAir conditioning\nPrivate bathroom\nTV\nHot water\nSitting area",
     "Two double beds and a sitting area, ideal for families travelling together.", ["204", "205"]),
    ("Executive Suite", "Suite fulaynimo", 110, 3, "1 king bed + sofa bed", 45,
     "Free Wi-Fi\nAir conditioning\nPrivate bathroom\nTV\nHot water\nLiving room\nMini fridge\nBalcony",
     "Our largest accommodation with a separate living room.", ["301", "302"]),
]
SERVICES = [
    ("Free Wi-Fi", "Wi-Fi bilaash ah", "fa-wifi", "Wi-Fi in rooms and public areas."),
    ("Secure parking", "Gaari dhigasho ammaan ah", "fa-car", "Safe on-site parking for guests."),
    ("Laundry", "Dharka dhaqista", "fa-shirt", "Laundry and ironing on request."),
    ("Restaurant", "Makhaayad", "fa-utensils", "Breakfast, lunch and dinner served daily."),
    ("Conference hall", "Hoolka shirka", "fa-people-roof", "Meeting space for workshops and events."),
    ("24-hour reception", "Maqaalka 24-saac", "fa-bell-concierge", "Staff available at any hour."),
]
MENU = {
    ("Breakfast", "Quraac"): [("Eggs & flatbread", "Ukun iyo laxoox", 3), ("Tea or coffee", "Shaah ama qahwo", 1)],
    ("Main dishes", "Cuntooyin ugu weyn"): [("Grilled chicken with rice", "Digaag la dubay iyo bariis", 7),
                                          ("Goat meat with rice", "Hilib riyo iyo bariis", 9)],
    ("Drinks", "Cabitaano"): [("Fresh juice", "Casiir cusub", 2), ("Soft drink", "Cabitaan qabow", 1)],
}


class Command(BaseCommand):
    help = "Create starter hotel content. Use --with-staff to also create sample staff logins."

    def add_arguments(self, parser):
        parser.add_argument("--with-staff", action="store_true", help="Create manager/reception/accounts logins with random passwords.")

    def handle(self, *args, **opts):
        SiteSetting.load()
        for order, (en, so, price, cap, bed, size, fac, desc, numbers) in enumerate(ROOM_TYPES):
            rt, _ = RoomType.objects.get_or_create(name_en=en, defaults=dict(
                name_so=so, price_per_night=price, capacity=cap, bed_type=bed, size_sqm=size,
                facilities_en=fac, description_en=desc, order=order))
            for n in numbers:
                Room.objects.get_or_create(number=n, defaults=dict(room_type=rt, floor=int(n[0])))
        for order, (en, so, icon, desc) in enumerate(SERVICES):
            Service.objects.get_or_create(name_en=en, defaults=dict(name_so=so, icon=icon, description_en=desc, order=order))
        for order, ((cen, cso), items) in enumerate(MENU.items()):
            cat, _ = MenuCategory.objects.get_or_create(name_en=cen, defaults=dict(name_so=cso, order=order))
            for en, so, price in items:
                MenuItem.objects.get_or_create(category=cat, name_en=en, defaults=dict(name_so=so, price=price))
        self.stdout.write(self.style.SUCCESS("Starter content created. Review prices and text in the dashboard."))

        if opts["with_staff"]:
            User = get_user_model()
            for username, name, role in [("manager", "Hotel Manager", "manager"),
                                         ("reception", "Receptionist", "receptionist"),
                                         ("accounts", "Accountant", "accountant")]:
                if User.objects.filter(username=username).exists():
                    continue
                password = get_random_string(14)
                user = User.objects.create_user(username=username, password=password, first_name=name)
                Employee.objects.create(user=user, full_name=name, role=role, position=name)
                self.stdout.write(f"  login: {username}   password: {password}   (role: {role}) – change it after first login")
