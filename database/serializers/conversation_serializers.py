from rest_framework import serializers

from database.models import RemoteEnrollement


class ChatStartSerializer(serializers.Serializer):
    patient_id = serializers.CharField(max_length=64)


class ChatSerializer(serializers.ModelSerializer):
    conv_id = serializers.CharField(read_only=True)
    conv_ids = serializers.ListField(
        child=serializers.CharField(), read_only=True
    )

    class Meta:
        model = RemoteEnrollement
        fields = [
            "conv_id",
            "conv_ids",
            "patient_id",
            "patient_name",
            "provider",
            "practice",
            "recency",
            "status",
            "practice_phone",
            "consented_at",
            "consent_version",
            "alert_at",
            "created_at",
            "updated_at",
        ]


class ChatMessagePayloadSerializer(serializers.Serializer):
    """Validates one patient message."""

    conv_id = serializers.CharField()
    text = serializers.CharField()


class ChatMessageResponseSerializer(serializers.Serializer):
    """Formats the unified API response for chat turns."""

    conv_id = serializers.CharField()
    response = serializers.CharField()
    status = serializers.CharField()
