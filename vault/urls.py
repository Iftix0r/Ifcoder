from django.urls import path

from . import views

app_name = "vault"

urlpatterns = [
    path("", views.home, name="home"),
    path("api-keys/", views.APIKeyListView.as_view(), name="api_key_list"),
    path("api-keys/add/", views.APIKeyCreateView.as_view(), name="api_key_add"),
    path("api-keys/<int:pk>/edit/", views.APIKeyUpdateView.as_view(), name="api_key_edit"),
    path("api-keys/<int:pk>/delete/", views.APIKeyDeleteView.as_view(), name="api_key_delete"),
    path("backups/", views.backup_list, name="backup_list"),
    path("backups/create/", views.backup_create, name="backup_create"),
    path("backups/<str:filename>/download/", views.backup_download, name="backup_download"),
    path("2fa/setup/", views.totp_setup, name="totp_setup"),
    path("2fa/backup-codes/", views.totp_backup_codes, name="totp_backup_codes"),
    path("2fa/verify/", views.totp_verify, name="totp_verify"),
    path("2fa/disable/", views.totp_disable, name="totp_disable"),
]
