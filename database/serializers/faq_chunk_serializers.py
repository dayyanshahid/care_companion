from rest_framework import serializers


class FaqChunkSerializer(serializers.Serializer):
    """Read serializer for a retrieved FAQ chunk.

    Chunks live in Qdrant, not in a Mongo collection, so this reads the
    `Chunk` the retrieval layer returns rather than a model row. The vector
    itself is never exposed.
    """

    id = serializers.CharField(read_only=True)
    category = serializers.CharField(read_only=True)
    question = serializers.CharField(read_only=True)
    answer = serializers.CharField(read_only=True)


class KnowledgeQuerySerializer(serializers.Serializer):
    """Validates a knowledge-base search request."""

    query = serializers.CharField()
    top_k = serializers.IntegerField(required=False, min_value=1, max_value=20)
