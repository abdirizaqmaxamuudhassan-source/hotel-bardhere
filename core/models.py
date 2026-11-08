from django.db import models


class SiteSetting(models.Model):
    """Single row holding every hotel detail the owner may want to change."""

    hotel_name = models.CharField(max_length=120, default="HOTEL BARDHERE HB")
    tagline_en = models.CharField("Tagline (English)", max_length=200,
                                  default="Comfort, calm and warm hospitality in the heart of Bardhere")
    tagline_so = models.CharField("Tagline (Somali)", max_length=200, blank=True,
                                  default="Raaxo, nabad iyo martiqaad diirran oo ku taal Bardheere")
    hero_image = models.ImageField(upload_to="site/", blank=True)
    about_image = models.ImageField(upload_to="site/", blank=True)

    about_en = models.TextField("Our story (English)", default=(
        "HOTEL BARDHERE HB gives travellers, business visitors, aid workers and families a dependable, "
        "comfortable place to stay in Bardhere. Edit this text in Dashboard > Website content > Site settings."))
    about_so = models.TextField("Our story (Somali)", blank=True, default=(
        "HOTEL BARDHERE HB wuxuu siiyaa socotada, ganacsatada, shaqaalaha gargaarka iyo qoysaska meel raaxo leh oo la isku halleyn karo "
        "oo ku taal Bardheere."))
    mission_en = models.TextField("Mission (English)", default="To welcome every guest with honest service, clean rooms and fair prices.")
    mission_so = models.TextField("Mission (Somali)", blank=True, default="In aan marti kasta ku soo dhowayno adeeg daacad ah, qolal nadiif ah iyo qiimo cadaalad ah.")
    vision_en = models.TextField("Vision (English)", default="To be the most trusted hotel in Gedo region and a model for hospitality in Somalia.")
    vision_so = models.TextField("Vision (Somali)", blank=True, default="In aan noqonno hudheelka ugu kalsoonida badan gobolka Gedo iyo tusaale martiqaad oo Soomaaliya ah.")

    address_en = models.CharField("Address (English)", max_length=250, default="Buundo, Baydhabo road, Bardhere, Gedo, Somalia")
    address_so = models.CharField("Address (Somali)", max_length=250, blank=True, default="Buundo, wadada Baydhabo, Bardheere, Gedo, Soomaaliya")
    phone = models.CharField(max_length=40, default="+252 000 000 000", help_text="Replace with the real hotel phone number.")
    whatsapp = models.CharField(max_length=40, default="+252000000000", help_text="International format, e.g. +2526XXXXXXXX")
    email = models.EmailField(default="info@example.com", help_text="Replace with the real hotel email.")
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    map_url = models.URLField("Google Maps link", blank=True, help_text="Link that opens the hotel on Google Maps.")

    currency_symbol = models.CharField(max_length=5, default="$")
    check_in_time = models.CharField(max_length=20, default="14:00")
    check_out_time = models.CharField(max_length=20, default="12:00")
    invoice_note = models.CharField(max_length=250, blank=True, default="Thank you for staying with us.")
    footer_text = models.CharField(max_length=250, blank=True)

    class Meta:
        verbose_name = "Site settings"
        verbose_name_plural = "Site settings"

    def __str__(self):
        return self.hotel_name

    def save(self, *args, **kwargs):
        self.pk = 1  # singleton
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def whatsapp_digits(self):
        return "".join(ch for ch in self.whatsapp if ch.isdigit())


class Service(models.Model):
    name_en = models.CharField("Name (English)", max_length=100)
    name_so = models.CharField("Name (Somali)", max_length=100, blank=True)
    description_en = models.TextField("Description (English)", blank=True)
    description_so = models.TextField("Description (Somali)", blank=True)
    icon = models.CharField(max_length=60, default="fa-concierge-bell",
                            help_text="Font Awesome class, e.g. fa-wifi, fa-car, fa-shirt, fa-utensils, fa-people-roof")
    is_active = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.name_en


class GalleryImage(models.Model):
    title_en = models.CharField("Title (English)", max_length=120, blank=True)
    title_so = models.CharField("Title (Somali)", max_length=120, blank=True)
    image = models.ImageField(upload_to="gallery/")
    is_active = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "-id"]

    def __str__(self):
        return self.title_en or f"Image {self.pk}"


class MenuCategory(models.Model):
    name_en = models.CharField("Name (English)", max_length=100)
    name_so = models.CharField("Name (Somali)", max_length=100, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name_plural = "Menu categories"

    def __str__(self):
        return self.name_en


class MenuItem(models.Model):
    category = models.ForeignKey(MenuCategory, on_delete=models.CASCADE, related_name="items")
    name_en = models.CharField("Name (English)", max_length=120)
    name_so = models.CharField("Name (Somali)", max_length=120, blank=True)
    description_en = models.CharField("Description (English)", max_length=250, blank=True)
    description_so = models.CharField("Description (Somali)", max_length=250, blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to="menu/", blank=True)
    is_available = models.BooleanField(default=True)

    class Meta:
        ordering = ["category__order", "id"]

    def __str__(self):
        return self.name_en


class ContactMessage(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    subject = models.CharField(max_length=160)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name}: {self.subject}"
