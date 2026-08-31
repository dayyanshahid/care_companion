from django_mongodb_backend.fields import ObjectIdField
from django.db import models


class Message(models.Model):
    """A single message in an enrollment chat.

    `conversation_id` is OpenAI's `conv_id`, which is what a transcript is
    read by and what the chat it belongs to is addressed by.
    `remoteenrollement_id` is that same chat's own `_id`, so a message joins
    back to the `remoteenrollement` collection without going through OpenAI's
    id.
    """

    remoteenrollement_id = ObjectIdField(db_index=True, null=True, blank=True)
    conversation_id = models.CharField(max_length=255, db_index=True)
    role = models.CharField(max_length=20)  # "user" or "assistant"
    text = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    ACTION_CHOICES = [
        (1, "created"),
        (2, "updated"),
        (3, "deleted"),
    ]
    action_type = models.IntegerField(choices=ACTION_CHOICES, default=1)

    class Meta:
        app_label = "database"
        db_table = "messages"
        ordering = ["created_at"]
