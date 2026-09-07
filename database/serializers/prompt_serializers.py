import hashlib

from bson import ObjectId
from rest_framework import serializers


class ObjectIdField(serializers.CharField):
    """A tenant id, as an ObjectId.

    A real 24-character ObjectId is kept as it is. Anything else is turned
    into one by hashing the text, so a caller may name a tenant however they
    like and still get a usable id. The mapping is fixed, so the same text
    always names the same tenant, and the id it produces maps to itself -
    either form reaches the same record.
    """

    def to_internal_value(self, data):
        value = super().to_internal_value(data).strip()

        if ObjectId.is_valid(value):
            return ObjectId(value)

        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()

        return ObjectId(digest[:24])


class TennetQuerySerializer(serializers.Serializer):
    """Whose prompt and documents to read."""

    tennet_id = ObjectIdField()


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

    `tennet_id` says whose record is being written and is always required; an
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
    tennet_id = ObjectIdField()
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
    tennet_id = serializers.CharField(allow_blank=True)
    files = PromptFileSerializer(many=True)
