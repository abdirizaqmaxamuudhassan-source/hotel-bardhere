from django.contrib import admin

from .models import Room, RoomImage, RoomType


class RoomImageInline(admin.TabularInline):
    model = RoomImage
    extra = 1


@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = ("name_en", "price_per_night", "capacity", "is_active")
    prepopulated_fields = {"slug": ("name_en",)}
    inlines = [RoomImageInline]


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("number", "room_type", "floor", "status")
    list_filter = ("room_type", "status")
