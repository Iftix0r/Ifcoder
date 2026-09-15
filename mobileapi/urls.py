from django.urls import path

from . import views

app_name = "mobileapi"

urlpatterns = [
    path("login/", views.ThrottledObtainAuthToken.as_view(), name="login"),
    path("tasks/", views.TaskListAPIView.as_view(), name="task_list"),
    path("tasks/<int:pk>/status/", views.TaskStatusUpdateAPIView.as_view(), name="task_status"),
    path("location/", views.LocationPingCreateAPIView.as_view(), name="location_ping"),
    path("device-token/", views.DeviceTokenRegisterAPIView.as_view(), name="device_token"),
]
