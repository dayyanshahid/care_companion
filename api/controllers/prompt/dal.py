from bson import ObjectId

from database.models import DocumentChunk, PromptFile, SystemPrompt
from utils.enums import ActionType


def find_prompt(tenant_id):
    return SystemPrompt.objects.filter(tenant_id=tenant_id).first()


def save_prompt(tenant_id, changes):
    prompt = find_prompt(tenant_id)

    if prompt is None:
        return SystemPrompt.objects.create(tenant_id=tenant_id, **changes)

    for field, value in changes.items():
        setattr(prompt, field, value)

    prompt.action_type = ActionType.Updated
    prompt.save()

    return prompt


def find_files(tenant_id):
    return PromptFile.objects.filter(tenant_id=tenant_id).order_by("created_at")


def find_file(file_id):
    if not ObjectId.is_valid(file_id):
        return None

    return PromptFile.objects.filter(id=ObjectId(file_id)).first()


def create_file(tenant_id, name, s3_key, content_type, size, text, content_hash):
    return PromptFile.objects.create(
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
    return DocumentChunk.objects.filter(tenant_id=tenant_id)


def create_chunks(tenant_id, file_id, pieces):
    """`pieces` is (text, embedding) in document order."""
    return DocumentChunk.objects.bulk_create(
        [
            DocumentChunk(
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
    DocumentChunk.objects.filter(file_id=file_id).delete()