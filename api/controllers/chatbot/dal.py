from database.models import Message
from utils.enums import ActionType

def create_message(conv_id, role, text):
    return Message.objects.create(
        conversation_id=conv_id,
        role=role,
        text=text,
    )


def find_messages(conv_id):
    return Message.objects.filter(
        conversation_id=conv_id,
    ).exclude(action_type=ActionType.Deleted).order_by("created_at")
