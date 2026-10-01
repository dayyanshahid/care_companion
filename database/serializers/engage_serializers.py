from rest_framework import serializers

from database.serializers.fields import ObjectIdField
from database.serializers.prompt_serializers import (
    PromptFileSerializer,
    UploadListField,
)


def optional():
    return serializers.CharField(required=False, allow_blank=True, default="")


def listed():
    return serializers.ListField(
        child=serializers.CharField(allow_blank=True),
        required=False,
        default=list,
    )


class EngageMessagePayloadSerializer(serializers.Serializer):
    conv_id = serializers.CharField()
    tenant_id = ObjectIdField()
    text = serializers.CharField()

    firstName = optional()
    lastName = optional()
    fullName = optional()
    patientAddress = optional()
    age = optional()
    gender = optional()
    dob = optional()
    mobilePhone = optional()
    email = optional()
    practiceName = optional()
    practice_phone = optional()
    providerName = optional()
    ehrId = optional()
    careManager = optional()
    careManagerId = optional()
    appointmentDate = optional()
    dataAge = optional()

    caregivers = listed()
    codes = listed()
    programs = listed()
    conditions = listed()
    medications = listed()
    vitals = listed()
    labs = listed()
    allergies = listed()
    goals = listed()
    barriers = listed()
    symptoms = listed()

    lastVisitNote = optional()
    dietGuidelines = optional()
    activityGuidelines = optional()
    carePlan = optional()
    upcomingAppointments = optional()
    nextCheckinAt = optional()
    lastCheckinSummary = optional()


class EngageMessageResponseSerializer(serializers.Serializer):
    conv_id = serializers.CharField()
    response = serializers.CharField()


class EngagePromptPayloadSerializer(serializers.Serializer):
    system_prompt = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    chatbot_name = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=120
    )
    tenant_id = ObjectIdField()
    updated_by = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    files = UploadListField(
        child=serializers.FileField(),
        required=False,
        default=list,
    )


class EngagePromptResponseSerializer(serializers.Serializer):
    system_prompt = serializers.CharField(allow_blank=True)
    chatbot_name = serializers.CharField(allow_blank=True)
    tenant_id = serializers.CharField(allow_blank=True)
    files = PromptFileSerializer(many=True)
