"""Drop the inline chat fields now that 0016 has copied them onto `Chat`."""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("database", "0016_move_chats_off_patients"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="conversation",
            name="conv_id",
        ),
        migrations.RemoveField(
            model_name="conversation",
            name="status",
        ),
    ]
