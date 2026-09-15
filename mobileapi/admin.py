from django.contrib import admin

from .models import DeviceToken, LocationPing


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "device_id", "updated_at")
    search_fields = ("user__username", "device_id", "fcm_token")

    def has_add_permission(self, request):
        # Tokenlar faqat mobil ilova orqali ro'yxatdan o'tadi.
        return False


@admin.register(LocationPing)
class LocationPingAdmin(admin.ModelAdmin):
    list_display = ("user", "latitude", "longitude", "recorded_at")
    list_filter = ("user",)
    search_fields = ("user__username",)

    def has_add_permission(self, request):
        # Joylashuv nuqtalari faqat mobil ilova orqali yaratiladi.
        return False
