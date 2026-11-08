from django.conf import settings
from django.db import models


class Employee(models.Model):
    MANAGER, RECEPTIONIST, ACCOUNTANT = "manager", "receptionist", "accountant"
    ROLE_CHOICES = [
        (MANAGER, "Manager (full access)"),
        (RECEPTIONIST, "Receptionist (bookings, customers, payments)"),
        (ACCOUNTANT, "Accountant (payments, reports, bookings)"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="employee")
    full_name = models.CharField(max_length=150)
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default=RECEPTIONIST)
    position = models.CharField("Job title", max_length=100, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    national_id = models.CharField("ID number", max_length=50, blank=True)
    salary = models.DecimalField("Monthly salary", max_digits=10, decimal_places=2, null=True, blank=True)
    hire_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name
