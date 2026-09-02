from django_mongodb_backend.fields import ObjectIdField
from django.db import models

from utils.enums import ActionType, MessageRole, choices


class Message(models.Model):
    tenant = models.CharField(max_length=100, db_index=True)

    remoteenrollement_id = ObjectIdField(db_index=True, null=True, blank=True)
    conversation_id = models.CharField(max_length=255, db_index=True)
    role = models.CharField(max_length=20, choices=choices(MessageRole))
    text = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    action_type = models.IntegerField(
        choices=choices(ActionType),
        default=ActionType.Created,
    )

    class Meta:
        app_label = "database"
        db_table = "messages"
        ordering = ["created_at"]