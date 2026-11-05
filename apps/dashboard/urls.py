from django.urls import path

from . import views

urlpatterns = [
    path("dashboard/", views.home, name="dashboard"),
    path("calendar/", views.calendar_view, name="calendar"),
]
