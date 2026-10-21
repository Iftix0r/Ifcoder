from django.contrib import admin

from .models import Project

for model in (Project,):
    admin.site.register(model)
