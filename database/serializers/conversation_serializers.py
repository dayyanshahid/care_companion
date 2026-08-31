from rest_framework import serializers

from database.models import RemoteEnrollement


class ChatStartSerializer(serializers.Serializer):
    """Validates a request to open a chat for one remote portal patient.

    Everything Emma needs about the patient is read from their capture, so
    which patient is the only thing asked for here.
    """

    patient_id = serializers.CharField(max_length=64)


class ChatSerializer(serializers.ModelSerializer):
    """One patient's enrollment record, as the list endpoint reports it.

    There is one record per patient, so `conv_ids` carries every conversation
    ever opened with them, oldest first, and `conv_id` is the newest of those
    - the one a transcript is read by. The record's own `_id` is not exposed.
    """

    # DRF has no mapping for the backend's ArrayField, so both are
    # declared - `conv_ids` to render as a list rather than its repr,
    # and `conv_id` because it is a property, not a field.
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
