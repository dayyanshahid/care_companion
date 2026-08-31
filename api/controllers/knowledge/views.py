"""Request/response handling for the knowledge (FAQ retrieval) module."""
from django.conf import settings
from rest_framework import status as http
from rest_framework.decorators import api_view
from rest_framework.response import Response

from api.controllers.knowledge import services
from database.serializers import FaqChunkSerializer, KnowledgeQuerySerializer


@api_view(["POST"])
def search_knowledge(request):
    """Return FAQ chunks ranked by relevance to a query (useful for testing)."""
    payload = KnowledgeQuerySerializer(data=request.data)
    payload.is_valid(raise_exception=True)

    top_k = payload.validated_data.get("top_k") or settings.RAG_TOP_K
    try:
        results = services.retrieve(payload.validated_data["query"], top_k=top_k)
    except services.KnowledgeError:
        return Response(
            {"detail": "Search is unavailable right now. Please try again."},
            status=http.HTTP_502_BAD_GATEWAY,
        )

    data = []
    for chunk, score in results:
        item = FaqChunkSerializer(chunk).data
        item["score"] = round(score, 4)
        data.append(item)
    return Response(data)
