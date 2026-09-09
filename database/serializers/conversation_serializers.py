from rest_framework import serializers

from database.serializers.fields import ObjectIdField


def optional():
    return serializers.CharField(required=False, allow_blank=True, default="")


class CaregiverSerializer(serializers.Serializer):
    name = optional()
    phone = optional()
    relationship = optional()
    email = optional()


class ConditionCodeSerializer(serializers.Serializer):
    code = optional()
    description = optional()
    conditionId = optional()
    parentConditionId = optional()
    other = serializers.BooleanField(required=False, default=False)
    status = optional()
    note = optional()


class ChatMessagePayloadSerializer(serializers.Serializer):
    tenant_id = ObjectIdField()
    conv_id = serializers.CharField()
    text = serializers.CharField(allow_blank=True)

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
    conv_id = serializers.CharField()
    response = serializers.CharField()