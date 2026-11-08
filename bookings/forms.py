import re
from datetime import timedelta

from django import forms
from django.utils import timezone

from rooms.models import RoomType

from .services import free_rooms

PHONE_RE = re.compile(r"^\+?[0-9][0-9 \-]{5,19}$")
MAX_NIGHTS = 60


def _css(form):
    for field in form.fields.values():
        w = field.widget
        w.attrs["class"] = "form-select" if isinstance(w, forms.Select) else "form-control"


class PublicBookingForm(forms.Form):
    full_name = forms.CharField(max_length=150)
    phone = forms.CharField(max_length=30)
    email = forms.EmailField(required=False)
    check_in = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    check_out = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    guests = forms.IntegerField(min_value=1, max_value=20, initial=1)
    room_type = forms.ModelChoiceField(queryset=RoomType.objects.none(), empty_label="—")
    special_requests = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}), max_length=1000)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["room_type"].queryset = RoomType.objects.filter(is_active=True)
        today = timezone.localdate()
        self.fields["check_in"].widget.attrs["min"] = today.isoformat()
        self.fields["check_out"].widget.attrs["min"] = (today + timedelta(days=1)).isoformat()
        _css(self)

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        if not PHONE_RE.match(phone):
            raise forms.ValidationError("Enter a valid phone number, e.g. +252 61 000 0000.")
        return phone

    def clean(self):
        cleaned = super().clean()
        ci, co = cleaned.get("check_in"), cleaned.get("check_out")
        rt, guests = cleaned.get("room_type"), cleaned.get("guests")
        if ci and ci < timezone.localdate():
            self.add_error("check_in", "Check-in cannot be in the past.")
        elif ci and co:
            if co <= ci:
                self.add_error("check_out", "Check-out must be after check-in.")
            elif (co - ci).days > MAX_NIGHTS:
                self.add_error("check_out", f"Online bookings are limited to {MAX_NIGHTS} nights. Please contact us for longer stays.")
            elif rt and not free_rooms(rt, ci, co).exists():
                self.add_error("room_type", "Sorry, this room type is fully booked for those dates. Try other dates or another room type.")
        if rt and guests and guests > rt.capacity:
            self.add_error("guests", f"{rt.name_en} holds at most {rt.capacity} guests.")
        return cleaned


class BookingLookupForm(forms.Form):
    reference = forms.CharField(max_length=12)
    phone = forms.CharField(max_length=30)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _css(self)
