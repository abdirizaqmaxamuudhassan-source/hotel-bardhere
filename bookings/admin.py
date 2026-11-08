from django.contrib import admin

from .models import Booking, Customer, Payment


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("full_name", "phone", "email")
    search_fields = ("full_name", "phone", "email")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("reference", "customer", "room", "check_in", "check_out", "total_price", "status")
    list_filter = ("status", "source")
    search_fields = ("reference", "customer__full_name", "customer__phone")
    readonly_fields = ("reference", "total_price")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "booking", "method", "amount", "status", "paid_at")
    list_filter = ("method", "status")
