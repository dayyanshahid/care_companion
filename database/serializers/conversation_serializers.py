from rest_framework import serializers

from database.models import RemoteEnrollement


class ChatStartSerializer(serializers.Serializer):
    """Validates a request to open a chat for one remote portal patient.

    Everything Emma needs about the patient is read from their capture, so
    which patient is the only thing asked for here.
    """

    patient_id = serializers.CharField(max_length=64)


class ChatSerializer(serializers.ModelSerializer):
    """One chat, as the list endpoint reports it.

    A chat is addressed by `conv_id` - OpenAI's id, and what the transcript is
    read by - everywhere it is addressed at all, so its own `_id` is not
    exposed.
    """

    class Meta:
        model = RemoteEnrollement
        fields = [
            "conv_id",
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
