from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

DEBUG = False
if SECRET_KEY.startswith("dev-") or not VAULT_FERNET_KEY:  # noqa: F405
    raise ImproperlyConfigured("Production uchun DJANGO_SECRET_KEY va IFCODER_FERNET_KEY o'rnatilishi shart.")

# cPanel/Passenger SSL'ni tashqarida tugatadi
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)  # noqa: F405
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

# Juda katta POST tanasi bilan xotirani band qilishni cheklaydi. Oddiy rasm/hujjatlar uchun 20 MB yetarli.
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"file": {"class": "logging.FileHandler", "filename": BASE_DIR / "logs" / "django.log"}},  # noqa: F405
    "loggers": {"django": {"handlers": ["file"], "level": "WARNING"}},
}
