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
    path("telegram/chats/<int:pk>/", views.chat, name="telegram_chat"),
    path("telegram/chats/<int:pk>/send/", views.send, name="telegram_send"),
    path("telegram/chats/<int:pk>/contact/", views.make_contact, name="telegram_contact"),
]
