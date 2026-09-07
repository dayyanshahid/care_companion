from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("database", "0038_systemprompt"),
    ]

    operations = [
        migrations.DeleteModel(
            name="SystemPrompt",
        ),
    ]
