from django.contrib import admin

from .models import DeviceToken, LocationPing


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "device_id", "brand", "os_version", "app_version", "last_seen_at", "last_ip")
    search_fields = ("user__username", "device_id", "brand", "fcm_token")

    def has_add_permission(self, request):
        # Tokenlar faqat mobil ilova orqali ro'yxatdan o'tadi.
        return False


@admin.register(LocationPing)
class LocationPingAdmin(admin.ModelAdmin):
    list_display = (
        "user", "latitude", "longitude", "battery_level", "battery_charging",
        "network_type", "recorded_at",
    )
    list_filter = ("user", "network_type")
    search_fields = ("user__username",)

    def has_add_permission(self, request):
        # Joylashuv nuqtalari faqat mobil ilova orqali yaratiladi.
        return False
