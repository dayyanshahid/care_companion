"""What the legally reviewed enrollment scripts need on the record.

`practice_phone` is the number the emergency script sends a patient to.
`consented_at` and `consent_version` are the consent record - the scripts
require consent to be retained and retrievable the way a signed form would
be, and the version says which wording was agreed. `alert_at` is stamped
when a patient reports a clinical symptom, so the chats a human still owes a
follow-up on can be found.

`status` gains `callback` and `optedout`, which the scripts create.
"""

import utils.enums
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("database", "0033_faq_chunks_back_to_mongodb"),
    ]

    operations = [
        migrations.AddField(
            model_name="remoteenrollement",
            name="alert_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="remoteenrollement",
            name="consent_version",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name="remoteenrollement",
            name="consented_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="remoteenrollement",
            name="practice_phone",
            field=models.CharField(blank=True, max_length=40),
        ),
        migrations.AlterField(
            model_name="remoteenrollement",
            name="status",
            field=models.CharField(
                choices=[
                    ("active", "active"),
                    ("enrolled", "enrolled"),
                    ("declined", "declined"),
                    ("callback", "callback"),
                    ("optedout", "optedOut"),
                ],
                default=utils.enums.ChatStatus["active"],
                max_length=20,
            ),
        ),
    ]
