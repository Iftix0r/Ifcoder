from django.contrib import admin

from .models import APIKey, BackupCode, TOTPDevice


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "updated_at")
    exclude = ("encrypted_value",)

    def has_add_permission(self, request):
        # Kalitlar faqat /panel/vault/ orqali (shifrlash formasi bilan) qo'shiladi.
        return False


@admin.register(TOTPDevice)
class TOTPDeviceAdmin(admin.ModelAdmin):
    list_display = ("user", "confirmed", "created_at")
    exclude = ("encrypted_secret",)

    def has_add_permission(self, request):
        return False
    # Delete ruxsati ataylab yoqilgan qoladi: 2FA'dan qulflanib qolgan
    # superuser shu yerdan o'z qurilmasini o'chirib, qayta sozlashi mumkin.


@admin.register(BackupCode)
class BackupCodeAdmin(admin.ModelAdmin):
    list_display = ("device", "used_at", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
