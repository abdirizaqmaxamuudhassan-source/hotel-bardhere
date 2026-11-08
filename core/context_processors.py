from .models import SiteSetting


def site(request):
    return {"site": SiteSetting.load(), "LANG": getattr(request, "LANG", "en")}
