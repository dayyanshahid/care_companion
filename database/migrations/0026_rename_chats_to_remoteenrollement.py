"""Rename the `chats` collection, and the field that points at it.

`chats` becomes `remoteenrollement`, and a message's `chat_id` becomes
`remoteenrollement_id`. Both are renames, not drops - the collection keeps its
documents and every message keeps the id it already held.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("database", "0025_remove_chat_care_companion_number_and_more"),
    ]

    operations = [
        migrations.AlterModelTable(
            name="chat",
            table="remoteenrollement",
        ),
        migrations.RenameField(
            model_name="message",
            old_name="chat_id",
            new_name="remoteenrollement_id",
        ),
    ]
