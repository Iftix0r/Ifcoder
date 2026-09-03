from django.urls import path

from . import views

app_name = "bots"

urlpatterns = [
    path("", views.BotListView.as_view(), name="list"),
    path("add/", views.BotCreateView.as_view(), name="add"),
    path("<int:pk>/", views.BotDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.BotUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.BotDeleteView.as_view(), name="delete"),
    path("telegram/webhook/", views.telegram_webhook, name="telegram_webhook"),
    path("userbot/", views.UserbotSettingsView.as_view(), name="userbot"),
    path("api/userbot-dialogs/", views.userbot_dialogs_api, name="userbot_dialogs_api"),
    path("api/userbot-sync-contact/", views.userbot_sync_contact_api, name="userbot_sync_contact_api"),
]
