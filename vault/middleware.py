from django.shortcuts import redirect
from django.urls import reverse


class TwoFactorMiddleware:
    """Gate /panel/* behind a TOTP check once a user has a confirmed device.

    /admin/ is intentionally left ungated: it's the lockout-recovery path — a
    superuser can log in there with just a password and delete their own
    TOTPDevice row if they lose access to their authenticator.
    """

    EXEMPT_PREFIX = "/panel/vault/2fa/"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.path.startswith("/panel/")
            and not request.path.startswith(self.EXEMPT_PREFIX)
            and request.user.is_authenticated
        ):
            device = getattr(request.user, "totp_device", None)
            if device and device.confirmed and not request.session.get("2fa_verified"):
                verify_url = reverse("vault:totp_verify")
                return redirect(f"{verify_url}?next={request.path}")
        return self.get_response(request)
