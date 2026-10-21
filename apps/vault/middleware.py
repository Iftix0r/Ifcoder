from django.shortcuts import redirect
from django.urls import reverse

from .models import TOTPDevice

SESSION_KEY = "2fa_ok"


class TwoFactorMiddleware:
    """2FA yoqilgan foydalanuvchi kod kiritmaguncha faqat tasdiqlash sahifasini ko'radi.

    /admin/ ham qamrab olinadi — kirish imkoni yo'qolsa: ``manage.py disable_2fa <username>``.
    """

    ALLOWED_PREFIXES = ("/static/", "/media/", "/favicon.ico", "/robots.txt")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and not request.session.get(SESSION_KEY):
            allowed = (reverse("2fa_verify"), reverse("logout"))
            if not request.path.startswith(self.ALLOWED_PREFIXES) and request.path not in allowed:
                if TOTPDevice.objects.filter(user=user, confirmed=True).exists():
                    return redirect(f"{reverse('2fa_verify')}?next={request.get_full_path()}")
        return self.get_response(request)
