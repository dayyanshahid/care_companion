from django_mongodb_backend.fields import ObjectIdField
from django.db import models

STATUS_CHOICES = [
    ("active", "active"),
    ("enrolled", "enrolled"),
    ("declined", "declined"),
    ("callback", "callback"),
]

# How long ago the patient was last seen. Drives the opener's wording.
RECENCY_CHOICES = [
    ("onemonth", "onemonth"),
    ("year", "year"),
]


class RemoteEnrollement(models.Model):
    """One remote enrollment - Emma's conversation with one patient.

    Lives in the `remoteenrollement` collection; Mongo assigns the `_id`.

    The details Emma needs are copied here from the patient's portal capture
    when the chat is opened, so a chat reads the same on every turn even if
    the portal is unreachable. Every field below is either read into a prompt
    or filled into an FAQ placeholder.

    `conv_id` is OpenAI's own conversation id and stays blank until the chat is
    opened, so we never spend a call on a chat nobody starts. The transcript
    lives in `Message`, linked by `conv_id`.
    """

    # The portal capture this chat was opened for - its own `_id`, as an
    # ObjectId, so it joins straight back to `onsiteenrollmentcaptures`.
    patient_id = ObjectIdField(db_index=True, null=True, blank=True)

    # What Emma knows about the patient, rendered from that capture at start.
    patient_profile = models.TextField(blank=True)

    # Filled into the opener, the system prompt, and the FAQ's placeholders.
    patient_name = models.CharField(max_length=120)
    provider = models.CharField(max_length=200, blank=True)
    practice = models.CharField(max_length=200, blank=True)
    recency = models.CharField(max_length=20, choices=RECENCY_CHOICES, default="year")

    # OpenAI's conversation id. Blank until the chat is opened.
    conv_id = models.CharField(max_length=255, blank=True, default="", db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    ACTION_CHOICES = [
        (1, "created"),
        (2, "updated"),
        (3, "deleted"),
    ]
    action_type = models.IntegerField(choices=ACTION_CHOICES, default=1)

    @property
    def started(self):
        """True once the chat has been opened and OpenAI knows about it."""
        return bool(self.conv_id)

    class Meta:
        app_label = "database"
        db_table = "remoteenrollement"
        ordering = ["-created_at"]
