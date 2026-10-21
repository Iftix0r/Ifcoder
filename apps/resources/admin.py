from django.contrib import admin

from .models import Resource

for model in (Resource,):
    admin.site.register(model)
