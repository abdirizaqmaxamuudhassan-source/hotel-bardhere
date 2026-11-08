from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from rooms.models import RoomType

from .forms import ContactForm
from .middleware import SUPPORTED_LANGS
from .models import GalleryImage, MenuCategory, MenuItem, Service


def set_language(request, code):
    if code in SUPPORTED_LANGS:
        request.session["lang"] = code
    target = request.GET.get("next") or request.META.get("HTTP_REFERER") or "/"
    if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()},
                                           require_https=request.is_secure()):
        target = "/"
    return redirect(target)


def home(request):
    return render(request, "public/home.html", {
        "room_types": RoomType.objects.filter(is_active=True)[:3],
        "all_room_types": RoomType.objects.filter(is_active=True),
        "services": Service.objects.filter(is_active=True)[:6],
        "menu_items": MenuItem.objects.filter(is_available=True).select_related("category")[:4],
        "gallery": GalleryImage.objects.filter(is_active=True)[:6],
    })


def about(request):
    return render(request, "public/about.html", {
        "services": Service.objects.filter(is_active=True),
    })


def services(request):
    return render(request, "public/services.html", {
        "services": Service.objects.filter(is_active=True),
    })


def restaurant(request):
    categories = MenuCategory.objects.prefetch_related("items").all()
    data = []
    for cat in categories:
        items = [i for i in cat.items.all() if i.is_available]
        if items:
            data.append((cat, items))
    return render(request, "public/restaurant.html", {"menu": data})


def gallery(request):
    return render(request, "public/gallery.html", {
        "images": GalleryImage.objects.filter(is_active=True),
    })


def contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            request.session["contact_sent"] = True
            return redirect("core:contact")
    else:
        form = ContactForm()
    sent = request.session.pop("contact_sent", False)
    return render(request, "public/contact.html", {"form": form, "sent": sent})
