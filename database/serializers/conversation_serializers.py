from rest_framework import serializers

from database.models import RemoteEnrollement
from utils.enums import MessageRole, choices


def optional():
    """A patient field the caller may omit; the prompt reads a blank as unknown."""
    return serializers.CharField(required=False, allow_blank=True, default="")


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


class ChatTurnSerializer(serializers.Serializer):
    """One earlier turn, as the caller replays it."""

    role = serializers.ChoiceField(choices=choices(MessageRole))
    content = serializers.CharField(allow_blank=True)


class ChatMessagePayloadSerializer(serializers.Serializer):
    """One stateless turn: the patient's record and their message, in full.

    Only conv_id and text are required. The rest personalises the reply, and
    every one of them is safe to leave out - the prompt and the scripts both
    fall back when a value is blank.

    `history` is the turns before this one, oldest first. The message being
    answered is `text`, so it does not belong in `history` as well.
    """

    conv_id = serializers.CharField()
    text = serializers.CharField()

    firstName = optional()
    lastName = optional()
    fullName = optional()
    dob = optional()
    ehrId = optional()
    mobilePhone = optional()
    email = optional()
    gender = optional()
    practiceName = optional()
    practice_phone = optional()
    providerName = optional()
    careManager = optional()
    appointmentDate = optional()
    dataAge = optional()

    history = ChatTurnSerializer(many=True, required=False, default=list)


class ChatMessageResponseSerializer(serializers.Serializer):
    """One turn's reply, and the conversation it belongs to."""

    conv_id = serializers.CharField()
    response = serializers.CharField()
