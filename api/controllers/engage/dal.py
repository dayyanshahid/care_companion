from database.models import (
    EngageDocumentChunk,
    EngageMessage,
    EngagePromptFile,
    EngageSystemPrompt,
)
from utils.enums import ActionType


# --- transcript ---

def create_message(conv_id, role, text):
    return EngageMessage.objects.create(
        conversation_id=conv_id,
        role=role,
        text=text,
    )


def find_messages(conv_id):
    return EngageMessage.objects.filter(
        conversation_id=conv_id,
    ).exclude(action_type=ActionType.Deleted).order_by("created_at")


# --- system prompt ---

def find_prompt(tenant_id):
    return EngageSystemPrompt.objects.filter(tenant_id=tenant_id).first()


def save_prompt(tenant_id, changes):
    prompt = find_prompt(tenant_id)

    if prompt is None:
        return EngageSystemPrompt.objects.create(tenant_id=tenant_id, **changes)

    for field, value in changes.items():
        setattr(prompt, field, value)

    prompt.action_type = ActionType.Updated
    prompt.save()

    return prompt


# --- uploaded documents ---

def find_files(tenant_id):
    return EngagePromptFile.objects.filter(tenant_id=tenant_id).order_by("created_at")


def create_file(tenant_id, name, s3_key, content_type, size, text, content_hash):
    return EngagePromptFile.objects.create(
        tenant_id=tenant_id,
        name=name,
        s3_key=s3_key,
        content_type=content_type,
        size=size,
        text=text,
        content_hash=content_hash,
    )


def update_file(record, s3_key, content_type, size, text, content_hash):
    record.s3_key = s3_key
    record.content_type = content_type
    record.size = size
    record.text = text
    record.content_hash = content_hash
    record.action_type = ActionType.Updated
    record.save()

    return record


def delete_file(record):
    record.delete()


def find_chunks(tenant_id):
    return EngageDocumentChunk.objects.filter(tenant_id=tenant_id)


def create_chunks(tenant_id, file_id, pieces):
    return EngageDocumentChunk.objects.bulk_create(
        [
            EngageDocumentChunk(
                tenant_id=tenant_id,
                file_id=file_id,
                ordinal=ordinal,
                text=text,
                embedding=embedding,
            )
            for ordinal, (text, embedding) in enumerate(pieces)
        ]
    )


def delete_chunks(file_id):
    EngageDocumentChunk.objects.filter(file_id=file_id).delete()
