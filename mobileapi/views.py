from django.core.cache import cache
from rest_framework import generics
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response
from rest_framework.views import APIView

from tasks.models import Task
from tasks.services import set_task_status

from .models import DeviceToken
from .serializers import (
    DeviceTokenSerializer,
    LocationPingSerializer,
    TaskSerializer,
    TaskStatusSerializer,
)

LOGIN_ATTEMPT_LIMIT = 5
LOGIN_ATTEMPT_WINDOW = 300  # soniya


class ThrottledObtainAuthToken(ObtainAuthToken):
    """dashboard.views.ThrottledLoginView bilan bir xil IP-throttling mantiqi."""

    def post(self, request, *args, **kwargs):
        ip = request.META.get("REMOTE_ADDR", "unknown")
        key = f"mobile-login-attempts:{ip}"
        if cache.get(key, 0) >= LOGIN_ATTEMPT_LIMIT:
            return Response(
                {"detail": "Juda ko'p noto'g'ri urinish. Keyinroq urinib ko'ring."},
                status=429,
            )
        response = super().post(request, *args, **kwargs)
        if response.status_code != 200:
            cache.set(key, cache.get(key, 0) + 1, LOGIN_ATTEMPT_WINDOW)
        else:
            cache.delete(key)
        return response


class TaskListAPIView(generics.ListAPIView):
    serializer_class = TaskSerializer

    def get_queryset(self):
        return (
            Task.objects.filter(assigned_to=self.request.user)
            .select_related("client", "project")
        )


class TaskStatusUpdateAPIView(APIView):
    def post(self, request, pk):
        task = Task.objects.filter(pk=pk, assigned_to=request.user).first()
        if not task:
            return Response({"ok": False}, status=404)
        serializer = TaskStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ok = set_task_status(task, serializer.validated_data["status"], request.user)
        return Response({"ok": ok, "status": task.status})


class LocationPingCreateAPIView(generics.CreateAPIView):
    serializer_class = LocationPingSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class DeviceTokenRegisterAPIView(APIView):
    def post(self, request):
        serializer = DeviceTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        DeviceToken.objects.update_or_create(
            fcm_token=serializer.validated_data["fcm_token"],
            defaults={
                "user": request.user,
                "device_id": serializer.validated_data.get("device_id", ""),
            },
        )
        return Response({"ok": True})
