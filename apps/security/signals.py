from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.dispatch import receiver

from . import services


@receiver(user_logged_in)
def logged_in(sender, request, user, **kwargs):
    services.on_login(request, user)


@receiver(user_login_failed)
def login_failed(sender, credentials, request=None, **kwargs):
    services.on_login_failed(request, credentials.get("username", ""))
