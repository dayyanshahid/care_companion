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

# Copied off the portal capture, and refreshed every time a conversation is
# opened, so a returning patient's record is never stale.
CAPTURED_FIELDS = (
    "patient_profile",
    "patient_name",
    "provider",
    "practice",
    "recency",
)


def started():
    """Every patient record that has had at least one chat opened on it."""
    return RemoteEnrollement.objects.filter(conv_ids__len__gt=0)


def find_by_conv_id(conv_id):
    """The one patient record that holds this conversation."""
    return RemoteEnrollement.objects.filter(conv_ids__contains=[conv_id]).first()


def describe_conversation(chat, conv_id):
    """One opened conversation, with its transcript, as the chat screen reads it."""
    return {
        "conv_id": conv_id,
        "conv_ids": chat.conv_ids,
        "patient_id": str(chat.patient_id) if chat.patient_id else None,
        "patient_name": chat.patient_name,
        "status": chat.status,
        "messages": read_messages(conv_id),
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


def capture_fields(capture):
    return {
        "patient_profile": portal.profile(capture),
        "patient_name": portal.full_name(capture),
        "provider": capture.get("primaryProviderName", ""),
        "practice": capture.get("practiceName", ""),
        "recency": portal.recency(capture),
    }


@api_view(["POST"])
def start_chat(request):
    """Open a conversation for one remote patient, and write Emma's first message.

    A patient has one record, however many times they are chatted to. If they
    already have one it is reused - refreshed from the portal, and the new
    conversation id appended to its `conv_ids` - so a second conversation
    never writes a second document, and the patient's whole transcript stays
    on one record.
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

    fields = capture_fields(capture)
    chat = RemoteEnrollement.objects.filter(patient_id=capture["_id"]).first()
    is_new_record = chat is None

    if is_new_record:
        chat = RemoteEnrollement.objects.create(patient_id=capture["_id"], **fields)
    else:
        for name, value in fields.items():
            setattr(chat, name, value)

        # A fresh conversation is a fresh approach, whatever the last one
        # ended as.
        chat.status = "active"
        chat.save(update_fields=[*CAPTURED_FIELDS, "status", "updated_at"])

    try:
        conv_id, _ = services.start_chat(chat)
    except services.ChatServiceError:
        # Only ever drop a record this request created. A returning patient's
        # record holds their earlier conversations and must survive.
        if is_new_record:
            chat.delete()

        return Response(ASSISTANT_DOWN, status=http.HTTP_502_BAD_GATEWAY)

    return Response(describe_conversation(chat, conv_id), status=http.HTTP_201_CREATED)


@api_view(["POST"])
def send_message(request):
    """Every turn after the opener."""
    payload = ChatMessagePayloadSerializer(data=request.data)
    payload.is_valid(raise_exception=True)

    conv_id = payload.validated_data["conv_id"]
    chat = find_by_conv_id(conv_id)

    if not chat:
        return Response(NO_CHAT, status=http.HTTP_404_NOT_FOUND)

    try:
        answer, status = services.reply_to(chat, conv_id, payload.validated_data["text"])
    except services.ChatServiceError:
        return Response(ASSISTANT_DOWN, status=http.HTTP_502_BAD_GATEWAY)

    output = ChatMessageResponseSerializer({
        "conv_id": conv_id,
        "response": answer,
        "status": status,
    })
    return Response(output.data)


@api_view(["GET"])
def list_conversations(request):
    """Every patient who has actually been chatted to, newest first.

    One row per patient, carrying all of their conversation ids.
    `?patient_id=<id>` narrows it to that one patient.
    """
    chats = started()
    patient_id = request.query_params.get("patient_id")

    if patient_id:
        if not ObjectId.is_valid(patient_id):
            return Response(BAD_PATIENT_ID, status=http.HTTP_400_BAD_REQUEST)

        chats = chats.filter(patient_id=ObjectId(patient_id))

    return Response(ChatSerializer(chats, many=True).data)


@api_view(["GET"])
def read_conversation(request, ident):
    """One route, read two ways - the two id formats cannot be confused.

    A patient id (a 24-character ObjectId) returns that patient's record, with
    every conversation id on it.
    A `conv_id` (OpenAI's, always `conv_`-prefixed) returns that one
    conversation's transcript.
    """
    if ObjectId.is_valid(ident):
        chats = started().filter(patient_id=ObjectId(ident))
        return Response(ChatSerializer(chats, many=True).data)

    return Response(read_messages(ident))


@api_view(["GET"])
def list_patients(request):
    """The remote patients a chat can be opened for."""
    try:
        return Response(portal.list_patients())
    except portal.PortalError:
        return Response(PORTAL_DOWN, status=http.HTTP_502_BAD_GATEWAY)
