from django_mongodb_backend.fields import ObjectIdField
from django.db import models

from utils.enums import ActionType, choices


class SystemPrompt(models.Model):
    """One tenant's prompt, overwritten in place.

    There is a row per `tennet_id` and no prompt anywhere else, so until a
    tenant's first update it has nothing to send.
    """

    body = models.TextField()
    chatbot_name = models.CharField(max_length=120, blank=True)
    tennet_id = ObjectIdField(db_index=True, null=True, blank=True)
    updated_by = models.CharField(max_length=120, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    action_type = models.IntegerField(
        choices=choices(ActionType),
        default=ActionType.Created,
    )

    class Meta:
        app_label = "database"
        db_table = "system_prompts"
