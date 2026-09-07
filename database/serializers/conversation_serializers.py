from rest_framework import serializers

from database.serializers.fields import ObjectIdField


def optional():
    """A patient field the caller may omit; a blank reads as unknown."""
    return serializers.CharField(required=False, allow_blank=True, default="")


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

    Only tenant_id, conv_id and text are required. The rest personalises the
    reply, and every one of them is safe to leave out.

    `tenant_id` says whose prompt and whose documents the assistant answers
    with; it never reads another tenant's.

    The conversation so far is not sent: it is read from the stored
    transcript for this conv_id.
    """

    tenant_id = ObjectIdField()
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
