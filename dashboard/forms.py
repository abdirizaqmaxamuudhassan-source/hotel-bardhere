from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.forms import inlineformset_factory

from bookings.models import Booking, Customer, Payment
from core.models import GalleryImage, MenuCategory, MenuItem, Service, SiteSetting
from rooms.models import Room, RoomImage, RoomType

from .access import modules_for
from .models import Employee

User = get_user_model()


class BootstrapModelForm(forms.ModelForm):
    """Applies Bootstrap classes and native date pickers to every field."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            w = field.widget
            if isinstance(w, forms.CheckboxInput):
                w.attrs["class"] = "form-check-input"
            elif isinstance(w, (forms.Select, forms.SelectMultiple)):
                w.attrs["class"] = "form-select"
            elif isinstance(w, forms.ClearableFileInput):
                w.attrs["class"] = "form-control"
            else:
                w.attrs["class"] = "form-control"
            if isinstance(field, forms.DateField):
                field.widget = forms.DateInput(attrs={"type": "date", "class": "form-control"}, format="%Y-%m-%d")


class StaffAuthForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"class": "form-control", "autofocus": True})
        self.fields["password"].widget.attrs.update({"class": "form-control"})

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not modules_for(user):
            raise forms.ValidationError("This account has no dashboard access. Ask the manager.", code="no_access")


class RoomTypeForm(BootstrapModelForm):
    class Meta:
        model = RoomType
        fields = ["name_en", "name_so", "slug", "price_per_night", "capacity", "bed_type", "size_sqm",
                  "description_en", "description_so", "facilities_en", "facilities_so",
                  "main_image", "is_active", "order"]
        widgets = {f: forms.Textarea(attrs={"rows": 3}) for f in
                   ("description_en", "description_so", "facilities_en", "facilities_so")}


RoomImageFormSet = inlineformset_factory(
    RoomType, RoomImage, fields=("image", "caption"), extra=3, can_delete=True,
    widgets={"image": forms.ClearableFileInput(attrs={"class": "form-control"}),
             "caption": forms.TextInput(attrs={"class": "form-control"})})


class RoomForm(BootstrapModelForm):
    class Meta:
        model = Room
        fields = ["number", "room_type", "floor", "status", "notes"]


class CustomerForm(BootstrapModelForm):
    class Meta:
        model = Customer
        fields = ["full_name", "phone", "email", "id_number", "address", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}


class BookingStaffForm(BootstrapModelForm):
    class Meta:
        model = Booking
        fields = ["customer", "room", "check_in", "check_out", "guests", "price_per_night",
                  "status", "source", "special_requests"]
        widgets = {"special_requests": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["room"].queryset = Room.objects.select_related("room_type").order_by("number")
        self.fields["room"].label_from_instance = lambda r: f"{r.number} – {r.room_type.name_en} (${r.room_type.price_per_night}/night)"
        self.fields["source"].initial = "walk_in"
        self.fields["status"].initial = Booking.CONFIRMED


class PaymentForm(BootstrapModelForm):
    class Meta:
        model = Payment
        fields = ["booking", "method", "amount", "transaction_reference", "payer_phone",
                  "paid_at", "status", "notes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["booking"].queryset = Booking.objects.exclude(status=Booking.CANCELLED).select_related("customer")
        self.fields["booking"].label_from_instance = lambda b: f"{b.reference} – {b.customer.full_name} (total {b.total_price})"


class EmployeeForm(BootstrapModelForm):
    username = forms.CharField(max_length=150, help_text="Used to log in to the dashboard.")
    password = forms.CharField(
        widget=forms.PasswordInput(render_value=False), required=False,
        help_text="Required for new employees. When editing, leave empty to keep the current password.")

    class Meta:
        model = Employee
        fields = ["full_name", "role", "position", "phone", "email", "national_id", "salary", "hire_date", "is_active"]

    field_order = ["full_name", "username", "password", "role", "position", "phone", "email",
                   "national_id", "salary", "hire_date", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.creating = not self.instance.pk
        self.fields["password"].widget.attrs["class"] = "form-control"
        self.fields["password"].widget.attrs["autocomplete"] = "new-password"
        if self.creating:
            self.fields["password"].required = True
        else:
            self.fields["username"].initial = self.instance.user.username if self.instance.user_id else ""
            self.fields["username"].disabled = True
            self.fields["username"].required = False

    def clean_username(self):
        username = self.cleaned_data.get("username", "").strip()
        if self.creating and User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_password(self):
        password = self.cleaned_data.get("password", "")
        if password:
            validate_password(password)
        return password

    def save(self, commit=True):
        emp = super().save(commit=False)
        if self.creating:
            emp.user = User.objects.create_user(
                username=self.cleaned_data["username"], password=self.cleaned_data["password"],
                email=emp.email, first_name=emp.full_name[:150])
        elif emp.user_id:
            if self.cleaned_data.get("password"):
                emp.user.set_password(self.cleaned_data["password"])
        if emp.user_id or emp.user:
            emp.user.is_active = emp.is_active
            emp.user.save()
        if commit:
            emp.save()
        return emp


class MenuCategoryForm(BootstrapModelForm):
    class Meta:
        model = MenuCategory
        fields = ["name_en", "name_so", "order"]


class MenuItemForm(BootstrapModelForm):
    class Meta:
        model = MenuItem
        fields = ["category", "name_en", "name_so", "description_en", "description_so", "price", "image", "is_available"]


class ServiceForm(BootstrapModelForm):
    class Meta:
        model = Service
        fields = ["name_en", "name_so", "description_en", "description_so", "icon", "is_active", "order"]
        widgets = {"description_en": forms.Textarea(attrs={"rows": 3}), "description_so": forms.Textarea(attrs={"rows": 3})}


class GalleryForm(BootstrapModelForm):
    class Meta:
        model = GalleryImage
        fields = ["image", "title_en", "title_so", "is_active", "order"]


class SiteSettingForm(BootstrapModelForm):
    class Meta:
        model = SiteSetting
        fields = "__all__"
        widgets = {f: forms.Textarea(attrs={"rows": 3}) for f in
                   ("about_en", "about_so", "mission_en", "mission_so", "vision_en", "vision_so")}
