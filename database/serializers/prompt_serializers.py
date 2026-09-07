from bson import ObjectId
from rest_framework import serializers

from utils.messages import messages


class ObjectIdField(serializers.CharField):
    """A tenant id: a real ObjectId, stored exactly as it was given.

    Nothing is derived or padded. An id that is not a 24-character ObjectId
    is refused rather than turned into some other tenant's id quietly.
    """

    def to_internal_value(self, data):
        value = super().to_internal_value(data).strip()

        if not ObjectId.is_valid(value):
            raise serializers.ValidationError(messages["invalidTenantId"])

        return ObjectId(value)


class TenantQuerySerializer(serializers.Serializer):
    """Whose prompt and documents to read."""

    tenant_id = ObjectIdField()


class UploadListField(serializers.ListField):
    """The uploaded files, with blank rows dropped before they are validated.

    A form row that is present but carries no file - Postman leaves one behind
    whenever a File row is enabled and nothing is picked - arrives as an empty
    value rather than a file. It means "no file", so it is discarded here.
    Anything else that is not a file still fails validation.
    """

    def get_value(self, dictionary):
        value = super().get_value(dictionary)

        if value in (serializers.empty, None):
            return value

        return [item for item in value if item not in ("", None)]


class PromptFileSerializer(serializers.Serializer):
    """One stored document: what it is called, and where to read it."""

    id = serializers.CharField()
    name = serializers.CharField()
    content_type = serializers.CharField(allow_blank=True)
    size = serializers.IntegerField()
    url = serializers.CharField(allow_blank=True)
    created_at = serializers.DateTimeField()


class SystemPromptPayloadSerializer(serializers.Serializer):
    """One tenant's update: a new prompt, name, documents, or any mix.

    `tenant_id` says whose record is being written and is always required; an
    update carrying nothing else is rejected. A field left out keeps whatever
    that tenant has stored, so the name survives a prompt-only update and the
    prompt survives a name-only one. Files add to what is stored; they never
    replace it.
    """

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


class SystemPromptResponseSerializer(serializers.Serializer):
    """The prompt in force, what the chatbot is called, and its documents."""

    system_prompt = serializers.CharField(allow_blank=True)
    chatbot_name = serializers.CharField(allow_blank=True)
    tenant_id = serializers.CharField(allow_blank=True)
    files = PromptFileSerializer(many=True)
