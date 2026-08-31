from bson import ObjectId
from rest_framework import status as http
from rest_framework.decorators import api_view
from rest_framework.response import Response

from api.controllers.chatbot import services
from database import portal
from database.models import Message, RemoteEnrollement
from database.serializers import (
    ChatMessagePayloadSerializer,
    ChatMessageResponseSerializer,
    ChatSerializer,
    ChatStartSerializer,
)

ASSISTANT_DOWN = {"detail": "The assistant is unavailable right now. Please try again."}
PORTAL_DOWN = {"detail": "The patient portal is unavailable right now. Please try again."}
NO_CHAT = {"detail": "Chat not found."}
NO_PATIENT = {"detail": "No remote patient with that id."}
BAD_PATIENT_ID = {"patient_id": ["Not a valid patient id."]}


def describe_conversation(chat):
    """One opened chat, with its transcript, as the chat screen reads it."""
    return {
        "conv_id": chat.conv_id,
        "patient_name": chat.patient_name,
        "status": chat.status,
        "messages": read_messages(chat.conv_id),
    }


def read_messages(conv_id):
    return [
        {
            "role": message.role,
            "text": message.text,
            "created_at": message.created_at,
        }
        for message in Message.objects.filter(conversation_id=conv_id).order_by("created_at")
    ]


@api_view(["POST"])
def start_chat(request):
    """Open a chat for one remote patient, and write Emma's first message.

    Everything Emma is told about the patient is copied off their portal
    capture here, once, so the chat holds its own copy from then on.
    """
    payload = ChatStartSerializer(data=request.data)
    payload.is_valid(raise_exception=True)

    patient_id = payload.validated_data["patient_id"]

    try:
        capture = portal.get_patient(patient_id)
    except portal.PortalError:
        return Response(PORTAL_DOWN, status=http.HTTP_502_BAD_GATEWAY)

    if not capture:
        return Response(NO_PATIENT, status=http.HTTP_404_NOT_FOUND)

    chat = RemoteEnrollement.objects.create(
        patient_id=capture["_id"],
        patient_profile=portal.profile(capture),
        patient_name=portal.full_name(capture),
        provider=capture.get("primaryProviderName", ""),
        practice=capture.get("practiceName", ""),
        recency=portal.recency(capture),
    )

    try:
        services.start_chat(chat)
    except services.ChatServiceError:
        chat.delete()
        return Response(ASSISTANT_DOWN, status=http.HTTP_502_BAD_GATEWAY)

    return Response(describe_conversation(chat), status=http.HTTP_201_CREATED)


@api_view(["POST"])
def send_message(request):
    """Every turn after the opener."""
    payload = ChatMessagePayloadSerializer(data=request.data)
    payload.is_valid(raise_exception=True)

    chat = RemoteEnrollement.objects.filter(
        conv_id=payload.validated_data["conv_id"]
    ).first()

    if not chat:
        return Response(NO_CHAT, status=http.HTTP_404_NOT_FOUND)

    try:
        answer, status = services.reply_to(chat, payload.validated_data["text"])
    except services.ChatServiceError:
        return Response(ASSISTANT_DOWN, status=http.HTTP_502_BAD_GATEWAY)

    output = ChatMessageResponseSerializer({
        "conv_id": chat.conv_id,
        "response": answer,
        "status": status,
    })
    return Response(output.data)


@api_view(["GET"])
def list_conversations(request):
    """Every chat that has actually been opened, newest first.

    `?patient_id=<id>` narrows it to one patient's chats - a patient can hold
    several, so this is how you read all of theirs back.
    """
    chats = RemoteEnrollement.objects.exclude(conv_id="")
    patient_id = request.query_params.get("patient_id")

    if patient_id:
        if not ObjectId.is_valid(patient_id):
            return Response(BAD_PATIENT_ID, status=http.HTTP_400_BAD_REQUEST)

        chats = chats.filter(patient_id=ObjectId(patient_id))

    return Response(ChatSerializer(chats, many=True).data)


@api_view(["GET"])
def read_conversation(request, ident):
    """One route, read two ways - the two id formats cannot be confused.

    A patient id (a 24-character ObjectId) lists that patient's chats.
    A `conv_id` (OpenAI's, always `conv_`-prefixed) returns that chat's
    transcript.
    """
    if ObjectId.is_valid(ident):
        chats = RemoteEnrollement.objects.exclude(conv_id="").filter(
            patient_id=ObjectId(ident)
        )
        return Response(ChatSerializer(chats, many=True).data)

    return Response(read_messages(ident))



@api_view(["GET"])
def list_patients(request):
    """The remote patients a chat can be opened for."""
    try:
        return Response(portal.list_patients())
    except portal.PortalError:
        return Response(PORTAL_DOWN, status=http.HTTP_502_BAD_GATEWAY)
