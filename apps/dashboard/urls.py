from django.urls import path

from . import views

urlpatterns = [
    path("dashboard/", views.home, name="dashboard"),
    path("notifications/", views.notifications, name="notifications"),
    path("notifications/read-all/", views.notifications_read_all, name="notifications_read_all"),
    path("notifications/<str:notification_id>/read/", views.notification_read, name="notification_read"),
    path("calendar/", views.calendar_view, name="calendar"),
]
