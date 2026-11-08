from .access import is_manager, modules_for


def access(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {"ACCESS": set(), "IS_MANAGER": False}
    return {"ACCESS": modules_for(user), "IS_MANAGER": is_manager(user)}
