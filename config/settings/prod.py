from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

DEBUG = False
if SECRET_KEY.startswith("dev-") or not VAULT_FERNET_KEY:  # noqa: F405
    raise ImproperlyConfigured("Production uchun DJANGO_SECRET_KEY va IFCODER_FERNET_KEY o'rnatilishi shart.")

# cPanel/Passenger SSL'ni tashqarida tugatadi
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)  # noqa: F405
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"file": {"class": "logging.FileHandler", "filename": BASE_DIR / "logs" / "django.log"}},  # noqa: F405
    "loggers": {"django": {"handlers": ["file"], "level": "WARNING"}},
}
