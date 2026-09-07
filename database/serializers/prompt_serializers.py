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
    """An update: a new prompt, a new chatbot name, new documents, or any mix.

    Every field is optional on its own, but an update carrying none of them is
    rejected. A field left out keeps whatever is stored, so the name survives a
    prompt-only update and the prompt survives a name-only one. Files add to
    what is stored; they never replace it.
    """

    system_prompt = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    chatbot_name = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=120
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
    """The prompt in force, what the chatbot is called, and its documents."""

    system_prompt = serializers.CharField(allow_blank=True)
    chatbot_name = serializers.CharField(allow_blank=True)
    files = PromptFileSerializer(many=True)
