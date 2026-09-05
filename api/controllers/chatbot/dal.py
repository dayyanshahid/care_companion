from bson import ObjectId
from database import portal
from database.models import Message, RemoteEnrollement
from utils.enums import ActionType, ChatStatus

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
    query = portal.list_patients(tenant)
    return query

def get_capture(tenant, patient_id):
    query = portal.get_patient(tenant, patient_id)
    return query

def upsert_chat(tenant, capture):
    fields = {
        "patient_profile": portal.profile(capture),
        "patient_name": portal.full_name(capture),
        "provider": capture.get("primaryProviderName", ""),
        "practice": capture.get("practiceName", ""),
        "practice_phone": portal.practice_phone(tenant, capture),
        "recency": portal.recency(capture),
    }

    query = RemoteEnrollement.objects.filter(
        tenant=tenant["key"],
        patient_id=capture["_id"],
    ).exclude(action_type=ActionType.Deleted)

    chat = query.first()

    if chat is None:
        chat = RemoteEnrollement.objects.create(
            tenant=tenant["key"], patient_id=capture["_id"], **fields
        )
        return chat, True

    for name, value in fields.items():
        setattr(chat, name, value)

    chat.status = ChatStatus.active
    chat.action_type = ActionType.Updated
    chat.save(
        update_fields=[*CAPTURED_FIELDS, "status", "action_type", "updated_at"]
    )
    return chat, False

def find_started_chats(patient_id=None):
    query = RemoteEnrollement.objects.filter(
        conv_ids__len__gt=0,
    ).exclude(action_type=ActionType.Deleted)

    if patient_id:
        query = query.filter(patient_id=ObjectId(patient_id))
    return query

def add_conversation(chat, conv_id):
    query = chat.add_conversation(conv_id)
    return query

def delete_chat(chat):
    query = chat.delete()
    return query

def create_message(conv_id, role, text):
    query = Message.objects.create(
        conversation_id=conv_id,
        role=role,
        text=text,
    )
    return query

def find_messages(conv_id):
    query = Message.objects.filter(
        conversation_id=conv_id,
    ).exclude(action_type=ActionType.Deleted).order_by("created_at")
    return query