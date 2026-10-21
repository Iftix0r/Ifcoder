from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["*"]
VAULT_FERNET_KEY = VAULT_FERNET_KEY or "ZGV2LW9ubHktZmVybmV0LWtleS1kby1ub3QtdXNlISE="  # noqa: F405
