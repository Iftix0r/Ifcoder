from django.urls import path

from . import views

urlpatterns = [
    path("vault/", views.vault_list, name="vault_list"),
    path("vault/new/", views.secret_create, name="secret_create"),
    path("vault/<int:pk>/", views.secret_edit, name="secret_edit"),
    path("vault/<int:pk>/delete/", views.secret_delete, name="secret_delete"),
    path("vault/<int:pk>/reveal/", views.secret_reveal, name="secret_reveal"),
    path("vault/<int:pk>/hide/", views.secret_hide, name="secret_hide"),
    path("2fa/setup/", views.twofa_setup, name="2fa_setup"),
    path("2fa/verify/", views.twofa_verify, name="2fa_verify"),
    path("2fa/disable/", views.twofa_disable, name="2fa_disable"),
    path("backups/new/", views.backup_create, name="backup_create"),
    path("backups/<str:name>/", views.backup_download, name="backup_download"),
]
