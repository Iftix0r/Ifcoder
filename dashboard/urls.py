from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("alerts/", views.alerts, name="alerts"),
    path("search/", views.search, name="search"),
    path("reports/", views.reports, name="reports"),
]
