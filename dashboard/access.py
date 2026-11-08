"""Role-based permissions. Superusers can do everything; other staff need an active Employee record."""
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

ALL_MODULES = {"dashboard", "bookings", "customers", "rooms", "payments", "reports", "employees", "menu", "content"}

ROLE_MODULES = {
    "manager": set(ALL_MODULES),
    "receptionist": {"dashboard", "bookings", "customers", "payments"},
    "accountant": {"dashboard", "bookings", "payments", "reports"},
}


def modules_for(user):
    if not user.is_authenticated or not user.is_active:
        return set()
    if user.is_superuser:
        return set(ALL_MODULES)
    employee = getattr(user, "employee", None)
    if employee and employee.is_active:
        return set(ROLE_MODULES.get(employee.role, ()))
    return set()


def is_manager(user):
    if user.is_superuser:
        return True
    employee = getattr(user, "employee", None)
    return bool(employee and employee.is_active and employee.role == "manager")


class StaffRequiredMixin:
    """Class-based views: set `module = "bookings"` etc."""
    module = None
    manager_only = False

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if self.module not in modules_for(request.user):
            raise PermissionDenied
        if self.manager_only and not is_manager(request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


def module_required(module, manager_only=False):
    """Decorator for function views."""
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if module not in modules_for(request.user):
                raise PermissionDenied
            if manager_only and not is_manager(request.user):
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return wrapper
    return decorator
