from django_mongodb_backend.fields import ArrayField, ObjectIdField
from django.db import models

from utils.enums import ActionType, ChatStatus, Recency, choices


class RemoteEnrollement(models.Model):
    """One remote enrollment - Emma's record for one patient.

    Lives in the `remoteenrollement` collection; Mongo assigns the `_id`.
    There is exactly one document per patient of one tenant. Opening a
    second, third or tenth conversation with the same patient does not write a second
    document - the new conversation id is appended to `conv_ids` on the one
    they already have, so a patient's whole history stays on one record.

    The details Emma needs are copied here from the patient's portal capture
    and refreshed each time a conversation is opened, so a chat reads the same
    on every turn even if the portal is unreachable. Every field below is
    either read into a prompt or filled into an FAQ placeholder.

    `conv_ids` holds OpenAI's conversation ids, oldest first, and is empty
    until the first chat is opened - we never spend a call on a chat nobody
    starts. The transcripts live in `Message`, each one linked back to this
    record by `remoteenrollement_id` and to its own conversation by
    `conversation_id`.
    """

    # The tenant this record belongs to - the `key` of its registry record.
    # Every tenant reads its patients from its own database, so a capture id
    # is only unique within one tenant: this scopes every lookup below, and
    # nothing here is ever read without it.
    tenant = models.CharField(max_length=100, db_index=True)

    # The portal capture this record was opened for - its own `_id`, as an
    # ObjectId, so it joins straight back to that tenant's
    # `onsiteenrollmentcaptures`. One record per patient, so this and the
    # tenant together are what a record is looked up by.
    patient_id = ObjectIdField(db_index=True, null=True, blank=True)

    # What Emma knows about the patient, rendered from that capture at start.
    patient_profile = models.TextField(blank=True)

    # Filled into the opener, the system prompt, and the FAQ's placeholders.
    patient_name = models.CharField(max_length=120)
    provider = models.CharField(max_length=200, blank=True)
    practice = models.CharField(max_length=200, blank=True)
    recency = models.CharField(
        max_length=20,
        choices=choices(Recency),
        default=Recency.year,
    )

    # Every OpenAI conversation ever opened for this patient, oldest first.
    # Empty until the first chat is opened.
    conv_ids = ArrayField(
        models.CharField(max_length=255),
        default=list,
        blank=True,
        db_index=True,
    )

    # The patient's standing on the programme, carried across conversations.
    status = models.CharField(
        max_length=20,
        choices=choices(ChatStatus),
        default=ChatStatus.active,
    )

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
