"""Move each patient's inline chat onto its own `Chat` document.

Before this, a patient carried one `conv_id` and one `status`. Every patient
that had actually started a chat gets one `Chat` holding those, which becomes
their first of possibly many. Patients who never opened their link carried no
chat, so they get none.

Messages are matched to their patient through the `conv_id` they already
carry, which is the only link that existed between the two.
"""
from django.db import migrations


def move_chats(apps, schema_editor):
    Conversation = apps.get_model("database", "Conversation")
    Chat = apps.get_model("database", "Chat")
    Message = apps.get_model("database", "Message")

    for patient in Conversation.objects.all():
        if not patient.conv_id:
            continue

        Chat.objects.create(
            patient_id=str(patient.pk),
            conv_id=patient.conv_id,
            status=patient.status or "active",
        )

        Message.objects.filter(conversation_id=patient.conv_id).update(
            patient_id=str(patient.pk)
        )


def fold_chats_back(apps, schema_editor):
    """Fold the newest chat back onto the patient, for a clean reverse."""
    Conversation = apps.get_model("database", "Conversation")
    Chat = apps.get_model("database", "Chat")

    for patient in Conversation.objects.all():
        chat = (
            Chat.objects.filter(patient_id=str(patient.pk))
            .order_by("-created_at")
            .first()
        )

        if not chat:
            continue

        patient.conv_id = chat.conv_id
        patient.status = chat.status
        patient.save(update_fields=["conv_id", "status"])


class Migration(migrations.Migration):

    dependencies = [
        ("database", "0015_chat_and_message_patient_id"),
    ]

    operations = [
        migrations.RunPython(move_chats, fold_chats_back),
    ]
