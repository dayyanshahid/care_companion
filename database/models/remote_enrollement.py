from django_mongodb_backend.fields import ArrayField, ObjectIdField
from django.db import models

from utils.enums import ActionType, ChatStatus, Recency, choices


class RemoteEnrollement(models.Model):
    tenant = models.CharField(max_length=100, db_index=True)
    patient_id = ObjectIdField(db_index=True, null=True, blank=True)
    patient_profile = models.TextField(blank=True)
    patient_name = models.CharField(max_length=120)
    provider = models.CharField(max_length=200, blank=True)
    practice = models.CharField(max_length=200, blank=True)
    practice_phone = models.CharField(max_length=40, blank=True)
    recency = models.CharField(
        max_length=20,
        choices=choices(Recency),
        default=Recency.year,
    )
    conv_ids = ArrayField(
        models.CharField(max_length=255),
        default=list,
        blank=True,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=choices(ChatStatus),
        default=ChatStatus.active,
    )
    consented_at = models.DateTimeField(null=True, blank=True)
    consent_version = models.CharField(max_length=20, blank=True)
    alert_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    action_type = models.IntegerField(
        choices=choices(ActionType),
        default=ActionType.Created,
    )

    @property
    def started(self):
        """True once a chat has been opened and OpenAI knows about it."""
        return bool(self.conv_ids)

    @property
    def conv_id(self):
        """The conversation currently being held - the newest one opened."""
        return self.conv_ids[-1] if self.conv_ids else ""

    def add_conversation(self, conv_id):
        """Record one more conversation against this patient."""
        if conv_id and conv_id not in self.conv_ids:
            self.conv_ids.append(conv_id)
            self.save(update_fields=["conv_ids", "updated_at"])

        return conv_id

    class Meta:
        app_label = "database"
        db_table = "remoteenrollement"
        ordering = ["-created_at"]
