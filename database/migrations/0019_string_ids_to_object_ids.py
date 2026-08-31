"""Rewrite the stored `capture_id` and `patient_id` values as real ObjectIds.

0018 changed the field types, but MongoDB stores whatever it was given, so
every existing document still holds a *string*. A query now sends an ObjectId
and matches none of them - `chats` would look empty and every capture would
look unimported.

This is done through raw PyMongo rather than the ORM: the models now declare
these fields as ObjectIdField, so reading the old string values back through
Django would fail validation before we could fix them.

`capture_id` is blank on rows that predate the capture flow. Those become
null, which is what the field now allows.
"""
from bson import ObjectId
from bson.errors import InvalidId
from django.db import migrations

# collection -> field holding an id that should be an ObjectId
TARGETS = (
    ("conversations", "capture_id"),
    ("chats", "patient_id"),
)


def to_object_ids(apps, schema_editor):
    database = schema_editor.connection.database

    for name, field in TARGETS:
        collection = database[name]

        for document in collection.find({field: {"$type": "string"}}):
            value = document[field]

            try:
                replacement = ObjectId(value) if value else None
            except (InvalidId, TypeError):
                # Not an id we can convert; null it rather than leave a string
                # the ORM cannot read back.
                replacement = None

            collection.update_one(
                {"_id": document["_id"]}, {"$set": {field: replacement}}
            )


def to_strings(apps, schema_editor):
    database = schema_editor.connection.database

    for name, field in TARGETS:
        collection = database[name]

        for document in collection.find({field: {"$type": "objectId"}}):
            collection.update_one(
                {"_id": document["_id"]},
                {"$set": {field: str(document[field])}},
            )

        # Nulls were empty strings before the field allowed them.
        collection.update_many({field: None}, {"$set": {field: ""}})


class Migration(migrations.Migration):

    dependencies = [
        ("database", "0018_capture_and_patient_object_ids"),
    ]

    operations = [
        migrations.RunPython(to_object_ids, to_strings),
    ]
