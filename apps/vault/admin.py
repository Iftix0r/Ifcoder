from django.contrib import admin

from .models import Secret, TOTPDevice


@admin.register(Secret)
class SecretAdmin(admin.ModelAdmin):
    list_display = ["name", "kind", "login", "project", "updated_at"]
    search_fields = ["name", "login"]
    exclude = ["encrypted_value"]


@admin.register(TOTPDevice)
class TOTPDeviceAdmin(admin.ModelAdmin):
    list_display = ["user", "confirmed", "created_at"]
