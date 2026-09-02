from rest_framework import serializers


class FaqChunkSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    category = serializers.CharField(read_only=True)
    question = serializers.CharField(read_only=True)
    answer = serializers.CharField(read_only=True)


class KnowledgeQuerySerializer(serializers.Serializer):
    """Validates a knowledge-base search request."""

    query = serializers.CharField()
    top_k = serializers.IntegerField(required=False, min_value=1, max_value=20)
