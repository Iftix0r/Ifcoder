from django.urls import path

from . import views

urlpatterns = [
    path("telegram/", views.home, name="telegram_home"),
    path("telegram/connect/", views.connect, name="telegram_connect"),
    path("telegram/code/", views.code, name="telegram_code"),
    path("telegram/password/", views.password, name="telegram_password"),
    path("telegram/cancel/", views.cancel, name="telegram_cancel"),
    path("telegram/logout/", views.logout, name="telegram_logout"),
    path("telegram/sync/", views.sync, name="telegram_sync"),
    path("telegram/options/", views.options, name="telegram_options"),
    path("telegram/open/", views.open_chat, name="telegram_open"),
    path("telegram/search/", views.search_messages, name="telegram_search"),
    path("telegram/replies/new/", views.reply_create, name="telegram_reply_create"),
    path("telegram/replies/<int:pk>/", views.reply_edit, name="telegram_reply_edit"),
    path("telegram/replies/<int:pk>/delete/", views.reply_delete, name="telegram_reply_delete"),
    path("telegram/chats/<int:pk>/task/", views.make_task, name="telegram_task"),
    path("telegram/unread/", views.unread_badge, name="telegram_unread"),
    path("telegram/voice/preview/", views.voice_preview, name="telegram_voice_preview"),
    path("telegram/debts/<int:pk>/remind/", views.debt_remind, name="telegram_debt_remind"),
    path("telegram/media/<int:pk>/", views.media, name="telegram_media"),
    path("telegram/outbox/<int:pk>/dismiss/", views.dismiss, name="telegram_dismiss"),
    path("telegram/chats/<int:pk>/", views.chat, name="telegram_chat"),
    path("telegram/chats/<int:pk>/delete/", views.delete_message, name="telegram_delete"),
    path("telegram/chats/<int:pk>/older/", views.older, name="telegram_older"),
    path("telegram/chats/<int:pk>/peek/", views.peek, name="telegram_peek"),
    path("telegram/chats/<int:pk>/send/", views.send, name="telegram_send"),
    path("telegram/chats/<int:pk>/contact/", views.make_contact, name="telegram_contact"),
]
