from django.contrib import admin

from .models import Note

for model in (Note,):
    admin.site.register(model)
