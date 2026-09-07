from django_mongodb_backend.fields import ArrayField, ObjectIdField
from django.db import models

from utils.enums import ActionType, choices


class DocumentChunk(models.Model):
    tenant_id = ObjectIdField(db_index=True, null=True, blank=True)
    file_id = ObjectIdField(db_index=True, null=True, blank=True)
    ordinal = models.IntegerField(default=0)

    text = models.TextField()
    embedding = ArrayField(models.FloatField(), default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    action_type = models.IntegerField(
        choices=choices(ActionType),
        default=ActionType.Created,
    )

    class Meta:
        app_label = "database"
        db_table = "document_chunks"
        ordering = ["ordinal"]
