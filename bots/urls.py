from django.urls import path

from . import views

app_name = "bots"

urlpatterns = [
    path("", views.BotListView.as_view(), name="list"),
    path("add/", views.BotCreateView.as_view(), name="add"),
    path("<int:pk>/", views.BotDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.BotUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.BotDeleteView.as_view(), name="delete"),
]
