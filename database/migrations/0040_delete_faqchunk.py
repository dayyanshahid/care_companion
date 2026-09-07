from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("database", "0039_delete_systemprompt"),
    ]

    operations = [
        migrations.DeleteModel(
            name="FaqChunk",
        ),
    ]
