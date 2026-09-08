from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from api.controllers.prompt import services
from database.serializers import (
    SystemPromptPayloadSerializer,
    TenantQuerySerializer,
)
from utils.common import response
from utils.messages import messages


@api_view(["GET"])
def get_prompt(request):
    query = TenantQuerySerializer(data=request.query_params)
    query.is_valid(raise_exception=True)

    return Response(
        response.success(
            messages["promptFetched"],
            data=services.read(query.validated_data["tenant_id"]),
        )
    )


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def update_prompt(request):
    payload = SystemPromptPayloadSerializer(data=request.data)
    payload.is_valid(raise_exception=True)

    return Response(
        response.success(
            messages["promptUpdated"],
            data=services.update(payload.validated_data),
        )
    )
