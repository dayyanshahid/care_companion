from rest_framework import serializers

from database.models import RemoteEnrollement


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
            "alert_at",
            "created_at",
            "updated_at",
        ]


class CaregiverSerializer(serializers.Serializer):
    """Someone else on the patient's record, and how they are related."""

    name = optional()
    phone = optional()
    relationship = optional()
    email = optional()


class ConditionCodeSerializer(serializers.Serializer):
    """One coded condition. `status` says whether it is confirmed."""

    code = optional()
    description = optional()
    conditionId = optional()
    parentConditionId = optional()
    other = serializers.BooleanField(required=False, default=False)
    status = optional()
    note = optional()


class ChatMessagePayloadSerializer(serializers.Serializer):
    """One stateless turn: the patient's record and their message, in full.

    Only conv_id and text are required. The rest personalises the reply, and
    every one of them is safe to leave out - the prompt and the scripts both
    fall back when a value is blank.

    The conversation so far is not sent: it is read from the stored
    transcript for this conv_id.
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
    careManagerId = optional()

    caregivers = CaregiverSerializer(many=True, required=False, default=list)
    codes = ConditionCodeSerializer(many=True, required=False, default=list)
    programs = serializers.ListField(
        child=serializers.CharField(allow_blank=True),
        required=False,
        default=list,
    )


class ChatMessageResponseSerializer(serializers.Serializer):
    """One turn's reply, and the conversation it belongs to."""

    conv_id = serializers.CharField()
    response = serializers.CharField()
