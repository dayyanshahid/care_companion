import django_mongodb_backend.fields
import utils.enums
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("database", "0047_documentchunk_promptfile_content_hash"),
    ]

    operations = [
        migrations.CreateModel(
            name="EngageMessage",
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
                ("conversation_id", models.CharField(db_index=True, max_length=255)),
                (
                    "role",
                    models.CharField(
                        choices=[("user", "user"), ("assistant", "assistant")],
                        max_length=20,
                    ),
                ),
                ("text", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "action_type",
                    models.IntegerField(
                        choices=[(1, "Created"), (2, "Updated"), (3, "Deleted")],
                        default=utils.enums.ActionType["Created"],
                    ),
                ),
            ],
            options={
                "db_table": "engage_messages",
                "ordering": ["created_at"],
            },
        ),
        migrations.CreateModel(
            name="EngageSystemPrompt",
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
                ("body", models.TextField()),
                ("chatbot_name", models.CharField(blank=True, max_length=120)),
                (
                    "tenant_id",
                    django_mongodb_backend.fields.ObjectIdField(
                        blank=True, db_index=True, null=True
                    ),
                ),
                ("updated_by", models.CharField(blank=True, max_length=120)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "action_type",
                    models.IntegerField(
                        choices=[(1, "Created"), (2, "Updated"), (3, "Deleted")],
                        default=utils.enums.ActionType["Created"],
                    ),
                ),
            ],
            options={
                "db_table": "engage_system_prompts",
            },
        ),
        migrations.CreateModel(
            name="EngagePromptFile",
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
                (
                    "tenant_id",
                    django_mongodb_backend.fields.ObjectIdField(
                        blank=True, db_index=True, null=True
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("s3_key", models.CharField(max_length=500)),
                ("content_type", models.CharField(blank=True, max_length=120)),
                ("size", models.IntegerField(default=0)),
                ("text", models.TextField(blank=True)),
                ("content_hash", models.CharField(blank=True, max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "action_type",
                    models.IntegerField(
                        choices=[(1, "Created"), (2, "Updated"), (3, "Deleted")],
                        default=utils.enums.ActionType["Created"],
                    ),
                ),
            ],
            options={
                "db_table": "engage_prompt_files",
                "ordering": ["created_at"],
            },
        ),
        migrations.CreateModel(
            name="EngageDocumentChunk",
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
                (
                    "tenant_id",
                    django_mongodb_backend.fields.ObjectIdField(
                        blank=True, db_index=True, null=True
                    ),
                ),
                (
                    "file_id",
                    django_mongodb_backend.fields.ObjectIdField(
                        blank=True, db_index=True, null=True
                    ),
                ),
                ("ordinal", models.IntegerField(default=0)),
                ("text", models.TextField()),
                (
                    "embedding",
                    django_mongodb_backend.fields.ArrayField(
                        base_field=models.FloatField(), blank=True, default=list
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "action_type",
                    models.IntegerField(
                        choices=[(1, "Created"), (2, "Updated"), (3, "Deleted")],
                        default=utils.enums.ActionType["Created"],
                    ),
                ),
            ],
            options={
                "db_table": "engage_document_chunks",
                "ordering": ["ordinal"],
            },
        ),
    ]
