from bson import ObjectId

from database import portal
from database.models import Message, RemoteEnrollement
from utils.enums import ChatStatus

PortalError = portal.PortalError

CAPTURED_FIELDS = (
    "patient_profile",
    "patient_name",
    "provider",
    "practice",
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

def find_chat_by_conversation(tenant, conv_id):
    return RemoteEnrollement.objects.filter(
        tenant=tenant["key"], conv_ids__contains=[conv_id]
    ).first()

def find_started_chats(tenant, patient_id=None):
    chats = RemoteEnrollement.objects.filter(
        tenant=tenant["key"], conv_ids__len__gt=0
    )

    if patient_id:
        chats = chats.filter(patient_id=ObjectId(patient_id))

    return chats

def add_conversation(chat, conv_id):
    return chat.add_conversation(conv_id)

def set_chat_status(chat, status):
    chat.status = status
    chat.save(update_fields=["status", "updated_at"])

def delete_chat(chat):
    chat.delete()

def create_message(chat, conv_id, role, text):
    return Message.objects.create(
        tenant=chat.tenant,
        remoteenrollement_id=chat.id,
        conversation_id=conv_id,
        role=role,
        text=text,
    )

def find_messages(tenant_key, conv_id):
    return Message.objects.filter(
        tenant=tenant_key, conversation_id=conv_id
    ).order_by("created_at")