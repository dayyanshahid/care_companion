"""Prompts and documents belong to a tenant, named by a real ObjectId.

`tennet_id` arrived in 0044 as free text, so a stored value may be anything a
caller typed. A 24-character hex string is the id it was always meant to be
and is converted; anything else never named a tenant and is cleared, which
leaves the row readable but outside every tenant's view.
"""

import django_mongodb_backend.fields
from bson import ObjectId
from django.db import migrations


def to_object_ids(apps, schema_editor):
    prompts = schema_editor.connection.database["system_prompts"]

    for document in prompts.find({}, {"tennet_id": 1}):
        stored = document.get("tennet_id")

        if isinstance(stored, ObjectId):
            continue

        value = (
            ObjectId(stored)
            if isinstance(stored, str) and ObjectId.is_valid(stored)
            else None
        )

        prompts.update_one(
            {"_id": document["_id"]}, {"$set": {"tennet_id": value}}
        )


def to_text(apps, schema_editor):
    prompts = schema_editor.connection.database["system_prompts"]

    for document in prompts.find({}, {"tennet_id": 1}):
        stored = document.get("tennet_id")

        prompts.update_one(
            {"_id": document["_id"]},
            {"$set": {"tennet_id": str(stored) if stored else ""}},
        )


class Migration(migrations.Migration):

    dependencies = [
        ("database", "0044_systemprompt_tennet_id"),
    ]

    operations = [
        migrations.RunPython(to_object_ids, to_text),
        migrations.AddField(
            model_name="promptfile",
            name="tennet_id",
            field=django_mongodb_backend.fields.ObjectIdField(
                blank=True, db_index=True, null=True
            ),
        ),
        migrations.AlterField(
            model_name="systemprompt",
            name="tennet_id",
            field=django_mongodb_backend.fields.ObjectIdField(
                blank=True, db_index=True, null=True
            ),
        ),
    ]
