from database.models import Message
from utils.enums import ActionType

def create_message(conv_id, role, text, action_type=ActionType.Created):
    return Message.objects.create(
        conversation_id=conv_id,
        role=role,
        text=text,
        action_type=action_type,
    )


def find_messages(conv_id):
    return Message.objects.filter(
        conversation_id=conv_id,
        action_type=ActionType.Created,
    ).order_by("created_at")


def next_queued(conv_id):
    return Message.objects.filter(
        conversation_id=conv_id,
        action_type=ActionType.Queued,
    ).order_by("created_at").first()


def mark_sent(message):
    message.action_type = ActionType.Created
    message.save(update_fields=["action_type", "updated_at"])

    return message
