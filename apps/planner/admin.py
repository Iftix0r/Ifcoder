from django.contrib import admin

from .models import Task, TimeEntry

for model in (
    Task,
    TimeEntry,
):
    admin.site.register(model)
