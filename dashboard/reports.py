"""Numbers behind the dashboard cards, charts and PDF report."""
from collections import OrderedDict, defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.utils import timezone

from bookings.models import Booking, Customer, Payment
from rooms.models import Room, RoomType


def completed_payments():
    return Payment.objects.filter(status=Payment.COMPLETED)


def total_revenue():
    return completed_payments().aggregate(s=Sum("amount"))["s"] or Decimal("0")


def room_counts(today=None):
    today = today or timezone.localdate()
    total = Room.objects.count()
    maintenance = Room.objects.filter(status=Room.MAINTENANCE).count()
    occupied = (Booking.objects.filter(status=Booking.CONFIRMED, check_in__lte=today, check_out__gt=today)
                .values("room_id").distinct().count())
    return {"total": total, "occupied": occupied, "maintenance": maintenance,
            "available": max(total - occupied - maintenance, 0)}


def revenue_series(period, today=None):
    """Returns (labels, values) for 'daily' (30 days), 'weekly' (12 weeks) or 'monthly' (12 months)."""
    today = today or timezone.localdate()
    buckets = OrderedDict()
    if period == "daily":
        start = today - timedelta(days=29)
        for i in range(30):
            d = start + timedelta(days=i)
            buckets[d] = Decimal("0")
        key = lambda d: d
        label = lambda k: k.strftime("%d %b")
    elif period == "weekly":
        monday = today - timedelta(days=today.weekday())
        start = monday - timedelta(weeks=11)
        for i in range(12):
            buckets[start + timedelta(weeks=i)] = Decimal("0")
        key = lambda d: d - timedelta(days=d.weekday())
        label = lambda k: "Wk " + k.strftime("%d %b")
    else:
        y, m = today.year, today.month
        months = []
        for _ in range(12):
            months.append((y, m))
            m -= 1
            if m == 0:
                y, m = y - 1, 12
        for ym in reversed(months):
            buckets[ym] = Decimal("0")
        start = date(months[-1][0], months[-1][1], 1)
        key = lambda d: (d.year, d.month)
        label = lambda k: date(k[0], k[1], 1).strftime("%b %Y")
    for paid_at, amount in completed_payments().filter(paid_at__gte=start, paid_at__lte=today).values_list("paid_at", "amount"):
        k = key(paid_at)
        if k in buckets:
            buckets[k] += amount
    return [label(k) for k in buckets], [float(v) for v in buckets.values()]


def occupancy_pct(start, end, room_type=None):
    """Share of room-nights sold (confirmed bookings) between start and end inclusive."""
    rooms = Room.objects.exclude(status=Room.MAINTENANCE)
    bookings = Booking.objects.filter(status=Booking.CONFIRMED, check_in__lte=end, check_out__gt=start)
    if room_type is not None:
        rooms = rooms.filter(room_type=room_type)
        bookings = bookings.filter(room__room_type=room_type)
    days = (end - start).days + 1
    capacity = rooms.count() * days
    if capacity == 0:
        return 0.0
    sold = 0
    end_excl = end + timedelta(days=1)
    for ci, co in bookings.values_list("check_in", "check_out"):
        sold += max((min(co, end_excl) - max(ci, start)).days, 0)
    return round(min(sold / capacity * 100, 100), 1)


def full_report(today=None):
    today = today or timezone.localdate()
    start30 = today - timedelta(days=29)

    revenue = {p: dict(zip(("labels", "values"), revenue_series(p, today))) for p in ("daily", "weekly", "monthly")}

    status_rows = {r["status"]: r["n"] for r in Booking.objects.values("status").annotate(n=Count("id"))}
    statuses = {
        "labels": ["Pending", "Confirmed", "Cancelled"],
        "values": [status_rows.get("pending", 0), status_rows.get("confirmed", 0), status_rows.get("cancelled", 0)],
    }
    source_rows = {r["source"]: r["n"] for r in Booking.objects.values("source").annotate(n=Count("id"))}

    popular = (Booking.objects.exclude(status=Booking.CANCELLED)
               .values("room__room_type__name_en").annotate(n=Count("id")).order_by("-n"))
    popular_types = {"labels": [r["room__room_type__name_en"] for r in popular],
                     "values": [r["n"] for r in popular]}

    occupancy = {"labels": [], "values": []}
    for rt in RoomType.objects.all():
        occupancy["labels"].append(rt.name_en)
        occupancy["values"].append(occupancy_pct(start30, today, rt))

    month_start = today.replace(day=1)
    repeat = Customer.objects.annotate(n=Count("bookings")).filter(n__gt=1).count()
    top_customers = [
        {"name": c.full_name, "phone": c.phone, "bookings": c.n}
        for c in Customer.objects.annotate(n=Count("bookings")).filter(n__gt=0).order_by("-n", "full_name")[:5]
    ]
    paid_by_method = {r["method"]: r["s"] for r in completed_payments().values("method").annotate(s=Sum("amount"))}
    method_labels = dict(Payment.METHOD_CHOICES)

    return {
        "today": today,
        "revenue": revenue,
        "revenue_30d": sum(revenue["daily"]["values"]),
        "revenue_total": float(total_revenue()),
        "statuses": statuses,
        "total_bookings": sum(statuses["values"]),
        "sources": {Booking(source=k).get_source_display(): v for k, v in source_rows.items()},
        "popular": popular_types,
        "occupancy": occupancy,
        "occupancy_overall": occupancy_pct(start30, today),
        "customers": {
            "total": Customer.objects.count(),
            "new_30d": Customer.objects.filter(created_at__date__gte=start30).count(),
            "new_month": Customer.objects.filter(created_at__date__gte=month_start).count(),
            "repeat": repeat,
            "top": top_customers,
        },
        "by_method": {method_labels.get(k, k): float(v) for k, v in paid_by_method.items()},
    }
