from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from api.controllers.prompt import services
from database.serializers import SystemPromptPayloadSerializer
from utils.common import response
from utils.messages import messages


@api_view(["GET"])
def get_prompt(request):
    """The prompt in force, and every document stored behind it."""
    return Response(
        response.success(messages["promptFetched"], data=services.read())
    )


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def update_prompt(request):
    """Overwrite the prompt, add documents, or both."""
    payload = SystemPromptPayloadSerializer(data=request.data)
    payload.is_valid(raise_exception=True)

    return Response(
        response.success(
            messages["promptUpdated"],
            data=services.update(payload.validated_data),
        )
    )


@api_view(["DELETE"])
def delete_prompt_file(request, file_id):
    """Remove one document. The others are untouched."""
    return Response(
        response.success(
            messages["promptFileDeleted"], data=services.remove(file_id)
        )
    )
