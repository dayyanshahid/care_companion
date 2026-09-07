from rest_framework import serializers


class PromptFileSerializer(serializers.Serializer):
    """One stored document: what it is called, and where to read it."""

    id = serializers.CharField()
    name = serializers.CharField()
    content_type = serializers.CharField(allow_blank=True)
    size = serializers.IntegerField()
    url = serializers.CharField(allow_blank=True)
    created_at = serializers.DateTimeField()


class SystemPromptPayloadSerializer(serializers.Serializer):
    """An update: new prompt text, new documents, or both.

    Both are optional on their own, but an update carrying neither is
    rejected. Files add to what is stored; they never replace it.
    """

    system_prompt = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    updated_by = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    files = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        default=list,
    )


class SystemPromptResponseSerializer(serializers.Serializer):
    """The prompt in force, and every document behind it."""

    system_prompt = serializers.CharField()
    files = PromptFileSerializer(many=True)
