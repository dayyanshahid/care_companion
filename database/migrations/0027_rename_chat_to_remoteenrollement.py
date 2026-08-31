"""Rename the model itself: `Chat` becomes `RemoteEnrollement`.

The collection was already renamed in 0026 and `db_table` still names it, so
nothing moves in Mongo here - this only brings the model's own name into line
with the collection it has been writing to since.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("database", "0026_rename_chats_to_remoteenrollement"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="Chat",
            new_name="RemoteEnrollement",
        ),
    ]
