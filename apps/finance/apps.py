from django.apps import AppConfig
from django.db.models.signals import post_migrate


def create_default_categories(sender, **kwargs):
    from .models import DEFAULT_CATEGORIES, Category

    if not Category.objects.exists():
        Category.objects.bulk_create(Category(name=n, kind=k, tone=t) for n, k, t in DEFAULT_CATEGORIES)


class FinanceConfig(AppConfig):
    name = "apps.finance"
    label = "finance"

    def ready(self):
        post_migrate.connect(create_default_categories, sender=self)
