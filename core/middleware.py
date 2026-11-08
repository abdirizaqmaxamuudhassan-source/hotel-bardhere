SUPPORTED_LANGS = ("en", "so")


class LanguageMiddleware:
    """Reads the visitor's language (English/Somali) from the session."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        lang = request.session.get("lang", "en")
        request.LANG = lang if lang in SUPPORTED_LANGS else "en"
        return self.get_response(request)
