from database.models import Message

def create_message(conv_id, role, text):
    return Message.objects.create(
        conversation_id=conv_id,
        role=role,
        text=text,
    )
