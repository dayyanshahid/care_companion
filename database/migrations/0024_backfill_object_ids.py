"""Bring existing rows up to the shapes 0023 declared.

Mongo does not rewrite documents when a field's type changes, so chats
written before 0023 still hold `patient_id` as a string, and their messages
have no `chat_id` at all. Both are filled in here.

A chat whose `patient_id` is not a valid ObjectId - there should be none -
is left alone rather than guessed at.
"""
from bson import ObjectId
from django.db import migrations


def to_object_ids(apps, schema_editor):
    Chat = apps.get_model("database", "Chat")
    Message = apps.get_model("database", "Message")

    for chat in Chat.objects.all():
        updates = []

        if isinstance(chat.patient_id, str) and ObjectId.is_valid(chat.patient_id):
            chat.patient_id = ObjectId(chat.patient_id)
            updates.append("patient_id")

        if updates:
            chat.save(update_fields=updates)

        if chat.conv_id:
            Message.objects.filter(
                conversation_id=chat.conv_id, chat_id=None
            ).update(chat_id=chat.id)


def to_strings(apps, schema_editor):
    Chat = apps.get_model("database", "Chat")
    Message = apps.get_model("database", "Message")

    for chat in Chat.objects.all():
        if chat.patient_id is not None:
            chat.patient_id = str(chat.patient_id)
            chat.save(update_fields=["patient_id"])

    Message.objects.update(chat_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ("database", "0023_message_chat_id_alter_chat_patient_id"),
    ]

    operations = [
        migrations.RunPython(to_object_ids, to_strings),
    ]
