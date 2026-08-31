"""Introduce `Chat` - one document per conversation - alongside the patient.

A patient held exactly one chat, inline on their own row. They can now hold
several, so the chat moves onto its own `chats` collection. The patient record
keeps its `conversations` collection and its `_id`, untouched.

`conv_id` and `status` still live on the patient here; 0016 copies them onto a
`Chat` and only then does 0017 drop them.
"""

import django_mongodb_backend.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("database", "0014_remove_conversation_cc_number_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Chat",
            fields=[
                (
                    "id",
                    django_mongodb_backend.fields.ObjectIdAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("patient_id", models.CharField(db_index=True, max_length=64)),
                (
                    "conv_id",
                    models.CharField(
                        blank=True, db_index=True, default="", max_length=255
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "active"),
                            ("enrolled", "enrolled"),
                            ("declined", "declined"),
                            ("callback", "callback"),
                        ],
                        default="active",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "action_type",
                    models.IntegerField(
                        choices=[(1, "created"), (2, "updated"), (3, "deleted")],
                        default=1,
                    ),
                ),
            ],
            options={
                "db_table": "chats",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddField(
            model_name="message",
            name="patient_id",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
    ]
