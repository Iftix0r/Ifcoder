from rest_framework import serializers

from tasks.models import Task

from .models import DeviceToken, LocationPing


class TaskSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.name", default="", read_only=True)
    client_phone = serializers.CharField(source="client.phone", default="", read_only=True)
    project_name = serializers.CharField(source="project.name", default="", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    priority_label = serializers.CharField(source="get_priority_display", read_only=True)

    class Meta:
        model = Task
        fields = [
            "id", "title", "description", "status", "status_label",
            "priority", "priority_label", "due_date",
            "client_name", "client_phone", "project_name",
        ]


class TaskStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Task.Status.choices)


class LocationPingSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocationPing
        fields = ["latitude", "longitude", "accuracy", "recorded_at"]


class DeviceTokenSerializer(serializers.Serializer):
    fcm_token = serializers.CharField(max_length=255)
    device_id = serializers.CharField(max_length=100, required=False, allow_blank=True)
