from django.urls import path

from . import views

app_name = "bookings"

urlpatterns = [
    path("", views.booking_create, name="create"),
    path("quote/", views.quote_api, name="quote"),
    path("status/", views.booking_status, name="status"),
    path("confirmation/<str:reference>/", views.confirmation, name="confirmation"),
]
