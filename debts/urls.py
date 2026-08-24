from django.urls import path

from . import views

app_name = "debts"

urlpatterns = [
    path("", views.DebtListView.as_view(), name="list"),
    path("add/", views.DebtCreateView.as_view(), name="add"),
    path("<int:pk>/", views.DebtDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.DebtUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.DebtDeleteView.as_view(), name="delete"),
]
