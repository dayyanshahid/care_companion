"""Request/response handling for the knowledge (FAQ retrieval) module.

Like the chatbot views: validate, call the service, pick the response. The
retrieval and its failures belong to `services`.
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response

from api.controllers.knowledge import services
from database.serializers import KnowledgeQuerySerializer
from utils.common import response
from utils.messages import messages


@api_view(["POST"])
def search_knowledge(request):
    """Return FAQ chunks ranked by relevance to a query (useful for testing)."""
    payload = KnowledgeQuerySerializer(data=request.data)
    payload.is_valid(raise_exception=True)

    result = services.search(
        payload.validated_data["query"],
        payload.validated_data.get("top_k"),
    )

    # A query nothing matches is a valid search, so it is still a success.
    if result:
        return Response(
            response.success(messages["searchCompleted"], data=result)
        )
    else:
        return Response(
            response.success(messages["noSearchResults"], data=result)
        )

