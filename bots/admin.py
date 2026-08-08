from django.contrib import admin

from .models import Bot


@admin.register(Bot)
class BotAdmin(admin.ModelAdmin):
    list_display = ("name", "platform", "status", "project", "client", "created_at")
    list_filter = ("platform", "status")
    search_fields = ("name", "username")
    autocomplete_fields = ("project", "client")
