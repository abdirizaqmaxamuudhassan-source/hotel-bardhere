from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "HOTEL BARDHERE HB – Django admin"
admin.site.site_title = "HOTEL BARDHERE HB"

urlpatterns = [
    path("admin/", admin.site.urls),  # advanced/technical admin (superusers only)
    path("manage/", include("dashboard.urls")),  # hotel staff dashboard
    path("rooms/", include("rooms.urls")),
    path("booking/", include("bookings.urls")),
    path("", include("core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
