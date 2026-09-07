from django.db import models

from utils.enums import ActionType, choices


class SystemPrompt(models.Model):
    """The one prompt the assistant runs on, overwritten in place.

    The only source of the prompt. Until the first update there is no row, and
    the assistant refuses to answer rather than inventing instructions.
    """

    body = models.TextField()
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
