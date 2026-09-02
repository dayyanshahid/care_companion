from django_mongodb_backend.fields import ArrayField
from django.db import models

from utils.enums import ActionType, choices


class FaqChunk(models.Model):
    category = models.CharField(max_length=200, blank=True)
    question = models.TextField()
    answer = models.TextField()

    embedding = ArrayField(models.FloatField(), default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    action_type = models.IntegerField(
        choices=choices(ActionType),
        default=ActionType.Created,
    )

    class Meta:
        app_label = "database"
        db_table = "faq_chunks"