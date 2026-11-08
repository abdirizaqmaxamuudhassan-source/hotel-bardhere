from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views as v

app_name = "dashboard"


def crud_paths(prefix, slug, views):
    return [
        path(f"{slug}/", views["list"], name=f"{prefix}_list"),
        path(f"{slug}/add/", views["add"], name=f"{prefix}_add"),
        path(f"{slug}/<int:pk>/edit/", views["edit"], name=f"{prefix}_edit"),
        path(f"{slug}/<int:pk>/delete/", views["delete"], name=f"{prefix}_delete"),
    ]


urlpatterns = [
    path("login/", v.StaffLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("", v.DashboardHome.as_view(), name="home"),

    # room types: custom form page (photo uploads); list and delete are generic
    path("room-types/", v.roomtype_views["list"], name="roomtype_list"),
    path("room-types/add/", v.roomtype_form, name="roomtype_add"),
    path("room-types/<int:pk>/edit/", v.roomtype_form, name="roomtype_edit"),
    path("room-types/<int:pk>/delete/", v.roomtype_views["delete"], name="roomtype_delete"),

    *crud_paths("room", "rooms", v.room_views),

    # customers
    path("customers/", v.customer_views["list"], name="customer_list"),
    path("customers/add/", v.customer_views["add"], name="customer_add"),
    path("customers/<int:pk>/", v.CustomerDetail.as_view(), name="customer_detail"),
    path("customers/<int:pk>/edit/", v.customer_views["edit"], name="customer_edit"),
    path("customers/<int:pk>/delete/", v.customer_views["delete"], name="customer_delete"),

    # bookings
    path("bookings/", v.booking_views["list"], name="booking_list"),
    path("bookings/add/", v.BookingAdd.as_view(), name="booking_add"),
    path("bookings/<int:pk>/", v.BookingDetail.as_view(), name="booking_detail"),
    path("bookings/<int:pk>/edit/", v.BookingEdit.as_view(), name="booking_edit"),
    path("bookings/<int:pk>/delete/", v.booking_views["delete"], name="booking_delete"),
    path("bookings/<int:pk>/status/", v.booking_status, name="booking_status"),
    path("bookings/<int:pk>/invoice/", v.booking_invoice, name="booking_invoice"),
    path("bookings/<int:pk>/invoice.pdf", v.booking_invoice_pdf, name="booking_invoice_pdf"),

    # payments
    path("payments/", v.payment_views["list"], name="payment_list"),
    path("payments/add/", v.PaymentAdd.as_view(), name="payment_add"),
    path("payments/<int:pk>/edit/", v.payment_views["edit"], name="payment_edit"),
    path("payments/<int:pk>/delete/", v.payment_views["delete"], name="payment_delete"),
    path("payments/<int:pk>/receipt/", v.payment_receipt, name="payment_receipt"),
    path("payments/<int:pk>/receipt.pdf", v.payment_receipt_pdf, name="payment_receipt_pdf"),

    *crud_paths("employee", "employees", v.employee_views),
    *crud_paths("menucat", "menu/categories", v.menucat_views),
    *crud_paths("menuitem", "menu/items", v.menuitem_views),
    *crud_paths("service", "content/services", v.service_views),
    *crud_paths("gallery", "content/gallery", v.gallery_views),
    path("content/settings/", v.site_settings, name="site_settings"),
    path("content/messages/", v.MessageList.as_view(), name="message_list"),
    path("content/messages/<int:pk>/", v.message_action, name="message_action"),

    path("reports/", v.analytics, name="reports"),
    path("reports/download.pdf", v.report_pdf, name="report_pdf"),
]
