from django.urls import path

from . import views

app_name = "clients"

urlpatterns = [
    path("", views.ClientListView.as_view(), name="list"),
    path("add/", views.ClientCreateView.as_view(), name="add"),
    path("<int:pk>/", views.ClientDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.ClientUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.ClientDeleteView.as_view(), name="delete"),
    path("<int:pk>/sync-tg-avatar/", views.client_sync_tg_avatar, name="sync_tg_avatar"),
    path("add-from-tg/", views.client_create_from_tg_api, name="add_from_tg_api"),
]


