from .base import *  # noqa: F403

DEBUG = False
SECRET_KEY = "test"
VAULT_FERNET_KEY = "ZGV2LW9ubHktZmVybmV0LWtleS1kby1ub3QtdXNlISE="
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
ALLOWED_HOSTS = ["*"]
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""
