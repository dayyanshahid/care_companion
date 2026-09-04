from bson import ObjectId
from django.utils import timezone

from database import portal
from database.models import Message, RemoteEnrollement
from utils.enums import ChatStatus

PortalError = portal.PortalError

CAPTURED_FIELDS = (
    "patient_profile",
    "patient_name",
    "provider",
    "practice",
    "practice_phone",
    "recency",
)

def is_object_id(value):
    return ObjectId.is_valid(value)

def list_captures(tenant):
    return portal.list_patients(tenant)

def get_capture(tenant, patient_id):
    return portal.get_patient(tenant, patient_id)

def upsert_chat(tenant, capture):

    fields = {
        "patient_profile": portal.profile(capture),
        "patient_name": portal.full_name(capture),
        "provider": capture.get("primaryProviderName", ""),
        "practice": capture.get("practiceName", ""),
        "practice_phone": portal.practice_phone(tenant, capture),
        "recency": portal.recency(capture),
    }

    chat = RemoteEnrollement.objects.filter(
        tenant=tenant["key"], patient_id=capture["_id"]
    ).first()

    if chat is None:
        chat = RemoteEnrollement.objects.create(
            tenant=tenant["key"], patient_id=capture["_id"], **fields
        )

        return chat, True

    for name, value in fields.items():
        setattr(chat, name, value)

    chat.status = ChatStatus.active
    chat.save(update_fields=[*CAPTURED_FIELDS, "status", "updated_at"])

    return chat, False

def find_started_chats(patient_id=None):
    chats = RemoteEnrollement.objects.filter(conv_ids__len__gt=0)

    if patient_id:
        chats = chats.filter(patient_id=ObjectId(patient_id))

    return chats

def add_conversation(chat, conv_id):
    return chat.add_conversation(conv_id)

def set_chat_status(chat, status):
    chat.status = status
    chat.save(update_fields=["status", "updated_at"])

def raise_alert(chat):
    if chat.alert_at:
        return chat.alert_at

    chat.alert_at = timezone.now()
    chat.save(update_fields=["alert_at", "updated_at"])

    return chat.alert_at

def delete_chat(chat):
    chat.delete()

def create_message(conv_id, role, text):
    """One stored turn. The conversation id is all that ties it to a chat."""
    return Message.objects.create(
        conversation_id=conv_id,
        role=role,
        text=text,
    )

def find_messages(conv_id):
    """The transcript. The conversation id names it on its own."""
    return Message.objects.filter(
        conversation_id=conv_id
    ).order_by("created_at")