from django_mongodb_backend.fields import ArrayField
from django.db import models

from utils.enums import ActionType, choices


class FaqChunk(models.Model):
    """One Q&A from the FAQ handbook, with the vector it is retrieved by.

    Lives in the `faq_chunks` collection. The FAQ is one shared knowledge
    base - it describes the Care Companion programme itself, not any one
    practice - so unlike every other collection here it is not scoped to a
    tenant.

    `embedding` is the OpenAI vector for the entry's text, stored alongside
    it. This MongoDB has no vector index, so retrieval scores the whole
    collection in Python; at a few dozen entries that costs less than the
    round trip would to search anywhere else.

    `ingest_faq` replaces every row at once, so ids are not stable across
    ingests and nothing should hold on to them.
    """

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
