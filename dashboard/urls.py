from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("alerts/", views.alerts, name="alerts"),
    path("search/", views.search, name="search"),
    path("ai/", views.ai_assistant, name="ai_assistant"),
    path("reports/", views.reports, name="reports"),
    path("operators/location/", views.operator_locations, name="operator_locations"),
    path("operators/location/live.json", views.operator_locations_live, name="operator_locations_live"),
    path(
        "operators/<int:user_id>/location/",
        views.operator_location_history,
        name="operator_location_history",
    ),
]
