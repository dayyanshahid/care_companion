from rest_framework.decorators import api_view
from rest_framework.response import Response

from api.controllers.chatbot import services
from database.serializers import (
    ChatMessagePayloadSerializer,
    ChatStartSerializer,
)
from utils import tenant as tenants
from utils.common import response
from utils.enums import HttpStatus
from utils.messages import messages


@api_view(["POST"])
def start_chat(request):
    tenant = tenants.from_request(request)

    payload = ChatStartSerializer(data=request.data)
    payload.is_valid(raise_exception=True)

    result = services.start_chat(
        tenant, payload.validated_data["patient_id"]
    )

    if result:
        started = (
            messages["chatStarted"]
            if result["email_sent"]
            else messages["chatStartedNoEmail"]
        )

        return Response(
            response.success(started, HttpStatus.created, result),
            status=HttpStatus.created,
        )
    else:
        return Response(
            response.error(messages["patientNotFound"], HttpStatus.notFound),
            status=HttpStatus.notFound,
        )


@api_view(["POST"])
def send_message(request):
    payload = ChatMessagePayloadSerializer(data=request.data)
    payload.is_valid(raise_exception=True)

    return Response(
        response.success(
            messages["messageSent"],
            data=services.send_message(payload.validated_data),
        )
    )


@api_view(["GET"])
def list_conversations(request):
    result = services.list_conversations(
        request.query_params.get("patient_id")
    )

    if result:
        return Response(
            response.success(messages["conversationsRetrieved"], data=result)
        )
    else:
        return Response(
            response.success(messages["noConversations"], data=result)
        )


@api_view(["GET"])
def read_conversation(request, ident):
    message, result = services.read_conversation(ident)

    if result:
        return Response(response.success(message, data=result))
    else:
        return Response(
            response.success(messages["nothingFound"], data=result)
        )


@api_view(["GET"])
def list_patients(request):
    tenant = tenants.from_request(request)

    result = services.list_patients(tenant)

    if result:
        return Response(
            response.success(messages["patientsRetrieved"], data=result)
        )
    else:
        return Response(response.success(messages["noPatients"], data=result))