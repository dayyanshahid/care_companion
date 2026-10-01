from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from api.controllers.engage import services
from database.serializers import (
    EngageMessagePayloadSerializer,
    EngagePromptPayloadSerializer,
    TenantQuerySerializer,
)
from utils.common import response
from utils.messages import messages


@api_view(["POST"])
def send_message(request):
    payload = EngageMessagePayloadSerializer(data=request.data)
    payload.is_valid(raise_exception=True)

    return Response(
        response.success(
            messages["engageMessageSent"],
            data=services.send_message(payload.validated_data),
        )
    )


@api_view(["GET"])
def get_prompt(request):
    query = TenantQuerySerializer(data=request.query_params)
    query.is_valid(raise_exception=True)

    return Response(
        response.success(
            messages["engagePromptFetched"],
            data=services.read(query.validated_data["tenant_id"]),
        )
    )


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def update_prompt(request):
    payload = EngagePromptPayloadSerializer(data=request.data)
    payload.is_valid(raise_exception=True)

    return Response(
        response.success(
            messages["engagePromptUpdated"],
            data=services.update(payload.validated_data),
        )
    )
