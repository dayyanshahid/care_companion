from bson import ObjectId

from database.models import PromptFile, SystemPrompt
from utils.enums import ActionType


def find_prompt():
    return SystemPrompt.objects.first()


def save_prompt(changes):
    prompt = find_prompt()

    if prompt is None:
        return SystemPrompt.objects.create(**changes)

    for field, value in changes.items():
        setattr(prompt, field, value)

    prompt.action_type = ActionType.Updated
    prompt.save()

    return prompt


def find_files():
    return PromptFile.objects.order_by("created_at")


def find_file(file_id):
    if not ObjectId.is_valid(file_id):
        return None

    return PromptFile.objects.filter(id=ObjectId(file_id)).first()


def create_file(name, s3_key, content_type, size, text):
    return PromptFile.objects.create(
        name=name,
        s3_key=s3_key,
        content_type=content_type,
        size=size,
        text=text,
    )


def delete_file(record):
    record.delete()