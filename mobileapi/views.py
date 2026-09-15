from django.core.cache import cache
from django.utils import timezone
from rest_framework import generics
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response
from rest_framework.views import APIView

from auditlog.models import AuditLog, log_action
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


def _client_ip(request):
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    return x_forwarded.split(",")[0].strip() if x_forwarded else request.META.get("REMOTE_ADDR")


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
        DeviceToken.objects.filter(user=self.request.user).update(
            last_seen_at=timezone.now(),
            last_ip=_client_ip(self.request),
        )


class DeviceTokenRegisterAPIView(APIView):
    def post(self, request):
        serializer = DeviceTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        device, _ = DeviceToken.objects.update_or_create(
            fcm_token=data["fcm_token"],
            defaults={
                "user": request.user,
                "device_id": data.get("device_id", ""),
                "brand": data.get("brand", ""),
                "os_version": data.get("os_version", ""),
                "sdk_int": data.get("sdk_int"),
                "app_version": data.get("app_version", ""),
                "last_seen_at": timezone.now(),
                "last_ip": _client_ip(request),
            },
        )
        log_action(
            user=request.user,
            action=AuditLog.Action.LOGIN,
            model_name="DeviceToken",
            object_id=device.id,
            object_repr=str(device),
            message=(
                f"Mobil ilova: {device.brand} {device.device_id}, "
                f"Android {device.os_version}, ilova v{device.app_version}"
            ).strip(),
            request=request,
        )
        return Response({"ok": True})
