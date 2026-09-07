from bson import ObjectId

from database.models import PromptFile, SystemPrompt
from utils.enums import ActionType


def find_prompt(tennet_id):
    return SystemPrompt.objects.filter(tennet_id=tennet_id).first()


def find_any_prompt():
    """Whatever prompt is stored, tenant or not. Only the chatbot reads this."""
    return SystemPrompt.objects.first()


def save_prompt(tennet_id, changes):
    prompt = find_prompt(tennet_id)

    if prompt is None:
        return SystemPrompt.objects.create(tennet_id=tennet_id, **changes)

    for field, value in changes.items():
        setattr(prompt, field, value)

    prompt.action_type = ActionType.Updated
    prompt.save()

    return prompt


def find_files(tennet_id):
    return PromptFile.objects.filter(tennet_id=tennet_id).order_by("created_at")


def find_all_files():
    """Every document, whoever owns it. Only the chatbot reads this."""
    return PromptFile.objects.order_by("created_at")


def find_file(file_id):
    if not ObjectId.is_valid(file_id):
        return None

    return PromptFile.objects.filter(id=ObjectId(file_id)).first()


def create_file(tennet_id, name, s3_key, content_type, size, text):
    return PromptFile.objects.create(
        tennet_id=tennet_id,
        name=name,
        s3_key=s3_key,
        content_type=content_type,
        size=size,
        text=text,
    )


def delete_file(record):
    record.delete()