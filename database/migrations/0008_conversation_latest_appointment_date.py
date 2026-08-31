from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("database", "0007_rename_openai_conv_id_conversation_conv_id")]

    operations = [
        migrations.RemoveField(model_name="conversation", name="recency"),
        migrations.AddField(
            model_name="conversation",
            name="latest_appointment_date",
            field=models.CharField(blank=True, default="", max_length=40),
            preserve_default=False,
        ),
    ]
