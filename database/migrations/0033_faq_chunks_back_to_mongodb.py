"""The FAQ comes back out of Qdrant and into MongoDB.

Chunks and their embeddings are rows in `faq_chunks` again, scored in Python
at query time. Nothing is copied across from Qdrant - run `ingest_faq` after
this to fill the collection.
"""

import django_mongodb_backend.fields
import utils.enums
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("database", "0032_tenant"),
    ]

    operations = [
        migrations.CreateModel(
            name="FaqChunk",
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
                ("category", models.CharField(blank=True, max_length=200)),
                ("question", models.TextField()),
                ("answer", models.TextField()),
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
                "db_table": "faq_chunks",
            },
        ),
    ]
