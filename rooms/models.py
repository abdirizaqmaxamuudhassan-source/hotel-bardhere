from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class RoomType(models.Model):
    """A category of room (Standard, Deluxe, Suite...). Price, photos and facilities live here."""

    name_en = models.CharField("Name (English)", max_length=100)
    name_so = models.CharField("Name (Somali)", max_length=100, blank=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True,
                            help_text="Leave empty to generate it from the English name.")
    description_en = models.TextField("Description (English)")
    description_so = models.TextField("Description (Somali)", blank=True)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    capacity = models.PositiveSmallIntegerField("Max guests", default=2)
    bed_type = models.CharField(max_length=80, blank=True, help_text="e.g. 1 double bed")
    size_sqm = models.PositiveSmallIntegerField("Size (m²)", null=True, blank=True)
    facilities_en = models.TextField("Facilities (English)", blank=True, help_text="One facility per line.")
    facilities_so = models.TextField("Facilities (Somali)", blank=True, help_text="One facility per line.")
    main_image = models.ImageField(upload_to="rooms/", blank=True)
    is_active = models.BooleanField("Show on website", default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "price_per_night"]

    def __str__(self):
        return self.name_en

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name_en) or "room"
            slug, n = base, 2
            while RoomType.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("rooms:detail", args=[self.slug])


class RoomImage(models.Model):
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="rooms/")
    caption = models.CharField(max_length=120, blank=True)

    def __str__(self):
        return self.caption or f"Photo {self.pk}"


class Room(models.Model):
    """One physical room (e.g. room 101)."""

    AVAILABLE = "available"
    MAINTENANCE = "maintenance"
    STATUS_CHOICES = [(AVAILABLE, "In service"), (MAINTENANCE, "Under maintenance")]

    number = models.CharField(max_length=10, unique=True)
    room_type = models.ForeignKey(RoomType, on_delete=models.PROTECT, related_name="rooms")
    floor = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=AVAILABLE)
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["number"]

    def __str__(self):
        return f"Room {self.number} ({self.room_type.name_en})"
