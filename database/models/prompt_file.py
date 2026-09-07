from django_mongodb_backend.fields import ObjectIdField
from django.db import models

from utils.enums import ActionType, choices


class PromptFile(models.Model):
    tenant_id = ObjectIdField(db_index=True, null=True, blank=True)
    name = models.CharField(max_length=255)
    s3_key = models.CharField(max_length=500)
    content_type = models.CharField(max_length=120, blank=True)
    size = models.IntegerField(default=0)
    text = models.TextField(blank=True)
    content_hash = models.CharField(max_length=64, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    action_type = models.IntegerField(
        choices=choices(ActionType),
        default=ActionType.Created,
    )

    class Meta:
        app_label = "database"
        db_table = "prompt_files"
        ordering = ["created_at"]
