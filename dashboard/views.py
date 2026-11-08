from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.db.models import Q, Sum
from django.db.models.deletion import ProtectedError
from django.db.models.fields.files import FieldFile
from django.db.models.manager import BaseManager
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView

from bookings.models import Booking, Customer, Payment
from core.models import ContactMessage, GalleryImage, MenuCategory, MenuItem, Service, SiteSetting
from rooms.models import Room, RoomType

from . import forms, pdf, reports
from .access import StaffRequiredMixin, is_manager, module_required
from .models import Employee


# ---------------------------------------------------------------- login ----
class StaffLoginView(LoginView):
    template_name = "dashboard/login.html"
    authentication_form = forms.StaffAuthForm
    redirect_authenticated_user = True
    MAX_ATTEMPTS, LOCK_SECONDS = 5, 15 * 60

    def _key(self):
        ip = self.request.META.get("REMOTE_ADDR", "?")
        return "login-fail:%s:%s" % (ip, slugify(self.request.POST.get("username", "").lower()))

    def post(self, request, *args, **kwargs):
        if cache.get(self._key(), 0) >= self.MAX_ATTEMPTS:
            messages.error(request, "Too many failed attempts. Please wait 15 minutes and try again.")
            return self.get(request, *args, **kwargs)
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        key = self._key()
        cache.set(key, cache.get(key, 0) + 1, self.LOCK_SECONDS)
        return super().form_invalid(form)

    def form_valid(self, form):
        cache.delete(self._key())
        return super().form_valid(form)


# ------------------------------------------------------------ dashboard ----
class DashboardHome(StaffRequiredMixin, TemplateView):
    module = "dashboard"
    template_name = "dashboard/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.localdate()
        active = Booking.objects.exclude(status=Booking.CANCELLED).select_related("customer", "room")
        labels, values = reports.revenue_series("daily", today)
        ctx.update(
            rooms=reports.room_counts(today),
            total_bookings=Booking.objects.count(),
            pending_count=Booking.objects.filter(status=Booking.PENDING).count(),
            checkins=active.filter(check_in=today),
            checkouts=active.filter(check_out=today),
            revenue=reports.total_revenue(),
            recent=Booking.objects.select_related("customer", "room__room_type")[:8],
            unread_messages=ContactMessage.objects.filter(is_read=False).count(),
            chart={"labels": labels[-7:], "values": values[-7:]},
            today=today,
        )
        return ctx


# ------------------------------------------------------ generic CRUD -------
def cell_value(obj, attr, kind=None):
    value = obj
    for part in attr.split("."):
        value = getattr(value, part, "")
        if callable(value) and not isinstance(value, BaseManager):  # related managers are callable too
            value = value()
    if isinstance(value, FieldFile):
        return {"kind": "image", "value": value.url if value else ""}
    if isinstance(value, bool):
        return {"kind": "bool", "value": value}
    if value in (None, ""):
        return {"kind": "text", "value": "—"}
    if kind == "badge":
        return {"kind": "badge", "value": value, "css": slugify(str(value))}
    return {"kind": "text", "value": value}


class CrudMixin(StaffRequiredMixin):
    title = ""
    prefix = ""   # URL names are dashboard:<prefix>_list / _add / _edit / _delete

    def url(self, action, *args):
        return reverse(f"dashboard:{self.prefix}_{action}", args=args)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(title=self.title, prefix=self.prefix, list_url=self.url("list"),
                   add_url=self.url("add"), module=self.module)
        return ctx


class CrudList(CrudMixin, ListView):
    template_name = "dashboard/crud_list.html"
    paginate_by = 20
    columns = []          # (label, attr) or (label, attr, "badge")
    search_fields = []
    filter_field = None
    detail = False        # add a "View" button (needs <prefix>_detail url)
    can_add = True
    manager_delete = False

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q and self.search_fields:
            cond = Q()
            for f in self.search_fields:
                cond |= Q(**{f + "__icontains": q})
            qs = qs.filter(cond)
        if self.filter_field:
            value = self.request.GET.get(self.filter_field, "")
            if value:
                qs = qs.filter(**{self.filter_field: value})
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        rows = []
        for obj in ctx["object_list"]:
            cells = [cell_value(obj, c[1], c[2] if len(c) > 2 else None) for c in self.columns]
            rows.append({
                "obj": obj, "cells": cells,
                "edit": self.url("edit", obj.pk), "delete": self.url("delete", obj.pk),
                "detail": self.url("detail", obj.pk) if self.detail else None,
            })
        choices = None
        if self.filter_field:
            choices = self.model._meta.get_field(self.filter_field).choices
        ctx.update(
            headers=[c[0] for c in self.columns], rows=rows, can_add=self.can_add,
            q=self.request.GET.get("q", ""), filter_field=self.filter_field, filter_choices=choices,
            filter_value=self.request.GET.get(self.filter_field, "") if self.filter_field else "",
            can_delete=(is_manager(self.request.user) or not self.manager_delete),
        )
        return ctx


class CrudSave(CrudMixin):
    template_name = "dashboard/crud_form.html"
    success_label = "Saved."

    def get_success_url(self):
        return self.url("list")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, self.success_label)
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)


class CrudCreate(CrudSave, CreateView):
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["heading"] = f"Add – {self.title}"
        return ctx


class CrudUpdate(CrudSave, UpdateView):
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["heading"] = f"Edit – {self.title}"
        return ctx


class CrudDelete(CrudMixin, DeleteView):
    template_name = "dashboard/crud_confirm_delete.html"

    def get_success_url(self):
        return self.url("list")

    def form_valid(self, form):
        try:
            self.object.delete()
        except ProtectedError:
            messages.error(self.request, "This record is linked to other records (for example bookings or payments) "
                                         "and cannot be deleted. Deactivate or cancel it instead.")
        else:
            self.after_delete()
            messages.success(self.request, "Deleted.")
        return redirect(self.get_success_url())

    def after_delete(self):
        pass


def crud(prefix, model, form, title, module, columns, search=(), filter_field=None, ordering=None,
         manager_delete=False, detail=False, list_extra=None, select_related=(), delete_cls=CrudDelete):
    """Builds the four views (list/add/edit/delete) for a model."""
    attrs = dict(model=model, prefix=prefix, title=title, module=module)
    list_attrs = dict(attrs, columns=columns, search_fields=list(search), filter_field=filter_field,
                      manager_delete=manager_delete, detail=detail)
    if ordering:
        list_attrs["ordering"] = ordering
    if select_related:
        list_attrs["queryset"] = model.objects.select_related(*select_related)
    list_attrs.update(list_extra or {})
    del_attrs = dict(attrs, manager_only=manager_delete)
    return {
        "list": type(f"{prefix}List", (CrudList,), list_attrs).as_view(),
        "add": type(f"{prefix}Add", (CrudCreate,), dict(attrs, form_class=form)).as_view(),
        "edit": type(f"{prefix}Edit", (CrudUpdate,), dict(attrs, form_class=form)).as_view(),
        "delete": type(f"{prefix}Delete", (delete_cls,), del_attrs).as_view(),
    }


# --- rooms ---
roomtype_views = crud("roomtype", RoomType, forms.RoomTypeForm, "Room types", "rooms",
                      [("Photo", "main_image"), ("Name", "name_en"), ("Price / night", "price_per_night"),
                       ("Max guests", "capacity"), ("Rooms", "rooms.count"), ("Visible", "is_active")],
                      search=["name_en", "name_so"])
room_views = crud("room", Room, forms.RoomForm, "Rooms", "rooms",
                  [("Number", "number"), ("Type", "room_type"), ("Floor", "floor"),
                   ("Status", "get_status_display", "badge"), ("Notes", "notes")],
                  search=["number", "room_type__name_en"], filter_field="status", select_related=["room_type"])


@module_required("rooms")
def roomtype_form(request, pk=None):
    """Room type + photo uploads in one page (inline formset)."""
    instance = get_object_or_404(RoomType, pk=pk) if pk else None
    form = forms.RoomTypeForm(request.POST or None, request.FILES or None, instance=instance)
    formset = forms.RoomImageFormSet(request.POST or None, request.FILES or None, instance=instance)
    if request.method == "POST":
        if form.is_valid():
            saved = form.save(commit=False)
            formset = forms.RoomImageFormSet(request.POST, request.FILES, instance=saved)
            if formset.is_valid():
                saved.save()
                form.save_m2m()
                formset.instance = saved
                formset.save()
                messages.success(request, "Room type saved.")
                return redirect("dashboard:roomtype_list")
        messages.error(request, "Please correct the errors below.")
    return render(request, "dashboard/roomtype_form.html", {
        "form": form, "formset": formset, "title": "Room types", "module": "rooms",
        "heading": "Edit room type" if instance else "Add room type", "list_url": reverse("dashboard:roomtype_list"),
    })


# --- customers ---
customer_views = crud("customer", Customer, forms.CustomerForm, "Customers", "customers",
                      [("Name", "full_name"), ("Phone", "phone"), ("Email", "email"),
                       ("Bookings", "bookings.count"), ("Registered", "created_at")],
                      search=["full_name", "phone", "email", "id_number"], manager_delete=True, detail=True)


class CustomerDetail(StaffRequiredMixin, DetailView):
    module = "customers"
    model = Customer
    template_name = "dashboard/customer_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        bookings = self.object.bookings.select_related("room__room_type").order_by("-check_in")
        ctx["bookings"] = bookings
        ctx["spent"] = Payment.objects.filter(booking__customer=self.object, status="completed").aggregate(s=Sum("amount"))["s"] or 0
        return ctx


# --- bookings ---
booking_views = crud("booking", Booking, forms.BookingStaffForm, "Reservations", "bookings",
                     [("Reference", "reference"), ("Guest", "customer.full_name"), ("Room", "room.number"),
                      ("Check-in", "check_in"), ("Check-out", "check_out"), ("Total", "total_price"),
                      ("Status", "get_status_display", "badge"), ("Payment", "payment_state", "badge")],
                     search=["reference", "customer__full_name", "customer__phone", "room__number"],
                     filter_field="status", manager_delete=True, detail=True,
                     select_related=["customer", "room__room_type"])


class BookingAdd(booking_views["add"].view_class):
    def get_initial(self):
        initial = super().get_initial()
        if self.request.GET.get("customer"):
            initial["customer"] = self.request.GET["customer"]
        return initial

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("dashboard:booking_detail", args=[self.object.pk])


class BookingEdit(booking_views["edit"].view_class):
    def get_success_url(self):
        return reverse("dashboard:booking_detail", args=[self.object.pk])


class BookingDetail(StaffRequiredMixin, DetailView):
    module = "bookings"
    template_name = "dashboard/booking_detail.html"
    queryset = Booking.objects.select_related("customer", "room__room_type")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["payments"] = self.object.payments.all()
        return ctx


@module_required("bookings")
@require_POST
def booking_status(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    new = request.POST.get("status")
    if new not in dict(Booking.STATUS_CHOICES):
        messages.error(request, "Unknown status.")
        return redirect("dashboard:booking_detail", pk=pk)
    booking.status = new
    try:
        booking.full_clean(exclude=["reference", "total_price", "created_by"])  # re-checks double booking
    except Exception as exc:
        messages.error(request, "; ".join(getattr(exc, "messages", [str(exc)])))
    else:
        booking.save()
        messages.success(request, f"Booking {booking.reference} is now {booking.get_status_display()}.")
    return redirect("dashboard:booking_detail", pk=pk)


# --- payments ---
class PaymentCreateMixin:
    def get_initial(self):
        initial = super().get_initial()
        booking_id = self.request.GET.get("booking")
        if booking_id and booking_id.isdigit():
            booking = Booking.objects.filter(pk=booking_id).first()
            if booking:
                initial.update(booking=booking.pk, amount=booking.balance_due or None)
        return initial


payment_views = crud("payment", Payment, forms.PaymentForm, "Payments", "payments",
                     [("Receipt", "receipt_number"), ("Date", "paid_at"), ("Booking", "booking.reference"),
                      ("Guest", "booking.customer.full_name"), ("Method", "get_method_display"),
                      ("Reference", "transaction_reference"), ("Amount", "amount"),
                      ("Status", "get_status_display", "badge")],
                     search=["booking__reference", "booking__customer__full_name", "transaction_reference"],
                     filter_field="status", manager_delete=True, select_related=["booking__customer"],
                     list_extra={"detail": False})


class PaymentAdd(PaymentCreateMixin, payment_views["add"].view_class):
    def form_valid(self, form):
        form.instance.received_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("dashboard:payment_receipt", args=[self.object.pk])


@module_required("payments")
def payment_receipt(request, pk):
    payment = get_object_or_404(Payment.objects.select_related("booking__customer", "booking__room__room_type", "received_by"), pk=pk)
    return render(request, "dashboard/receipt.html", {"payment": payment, "booking": payment.booking})


@module_required("payments")
def payment_receipt_pdf(request, pk):
    payment = get_object_or_404(Payment.objects.select_related("booking__customer", "booking__room__room_type"), pk=pk)
    resp = HttpResponse(pdf.receipt_pdf(payment, SiteSetting.load()), content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="{payment.receipt_number}.pdf"'
    return resp


@module_required("bookings")
def booking_invoice(request, pk):
    booking = get_object_or_404(Booking.objects.select_related("customer", "room__room_type"), pk=pk)
    return render(request, "dashboard/invoice.html", {
        "booking": booking, "payments": booking.payments.filter(status="completed").order_by("paid_at")})


@module_required("bookings")
def booking_invoice_pdf(request, pk):
    booking = get_object_or_404(Booking.objects.select_related("customer", "room__room_type"), pk=pk)
    resp = HttpResponse(pdf.invoice_pdf(booking, SiteSetting.load()), content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="INV-{booking.reference}.pdf"'
    return resp


# --- employees ---
class EmployeeDelete(CrudDelete):
    def form_valid(self, form):
        user = self.object.user
        if user and user == self.request.user:
            messages.error(self.request, "You cannot delete your own account.")
            return redirect(self.get_success_url())
        response = super().form_valid(form)
        if user and not Employee.objects.filter(user=user).exists() and not user.is_superuser:
            try:
                user.delete()
            except ProtectedError:
                user.is_active = False
                user.save()
        return response


employee_views = crud("employee", Employee, forms.EmployeeForm, "Employees", "employees",
                      [("Name", "full_name"), ("Login", "user.username"), ("Role", "get_role_display"),
                       ("Job title", "position"), ("Phone", "phone"), ("Salary", "salary"), ("Active", "is_active")],
                      search=["full_name", "phone", "position", "user__username"],
                      manager_delete=True, delete_cls=EmployeeDelete)

# --- restaurant menu & website content ---
menucat_views = crud("menucat", MenuCategory, forms.MenuCategoryForm, "Menu categories", "menu",
                     [("Name (English)", "name_en"), ("Name (Somali)", "name_so"), ("Order", "order"), ("Items", "items.count")],
                     search=["name_en", "name_so"])
menuitem_views = crud("menuitem", MenuItem, forms.MenuItemForm, "Menu items", "menu",
                      [("Photo", "image"), ("Name", "name_en"), ("Category", "category"), ("Price", "price"), ("Available", "is_available")],
                      search=["name_en", "name_so", "category__name_en"], select_related=["category"])
service_views = crud("service", Service, forms.ServiceForm, "Services", "content",
                     [("Name", "name_en"), ("Icon", "icon"), ("Order", "order"), ("Visible", "is_active")], search=["name_en"])
gallery_views = crud("gallery", GalleryImage, forms.GalleryForm, "Gallery photos", "content",
                     [("Photo", "image"), ("Title", "title_en"), ("Order", "order"), ("Visible", "is_active")])


@module_required("content")
def site_settings(request):
    instance = SiteSetting.load()
    form = forms.SiteSettingForm(request.POST or None, request.FILES or None, instance=instance)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Website settings saved.")
            return redirect("dashboard:site_settings")
        messages.error(request, "Please correct the errors below.")
    return render(request, "dashboard/crud_form.html", {
        "form": form, "title": "Site settings", "heading": "Site settings & website content", "module": "content",
        "list_url": reverse("dashboard:home"), "is_settings": True})


class MessageList(StaffRequiredMixin, ListView):
    module = "content"
    model = ContactMessage
    paginate_by = 20
    template_name = "dashboard/messages.html"


@module_required("content")
@require_POST
def message_action(request, pk):
    msg = get_object_or_404(ContactMessage, pk=pk)
    action = request.POST.get("action")
    if action == "delete":
        msg.delete()
        messages.success(request, "Message deleted.")
    else:
        msg.is_read = action == "read"
        msg.save(update_fields=["is_read"])
    return redirect("dashboard:message_list")


# --- analytics ---
@module_required("reports")
def analytics(request):
    report = reports.full_report()
    return render(request, "dashboard/reports.html", {"report": report, "module": "reports"})


@module_required("reports")
def report_pdf(request):
    period = request.GET.get("period", "monthly")
    if period not in ("daily", "weekly", "monthly"):
        period = "monthly"
    report = reports.full_report()
    resp = HttpResponse(pdf.report_pdf(report, period, SiteSetting.load()), content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="hotel-report-{timezone.localdate():%Y-%m-%d}.pdf"'
    return resp
