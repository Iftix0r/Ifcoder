from django.contrib import admin

from .models import Activity, Contact, Deal

for model in (
    Contact,
    Deal,
    Activity,
):
    admin.site.register(model)
