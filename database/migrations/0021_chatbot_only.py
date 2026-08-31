"""Fold the patient record into the chat, and drop it.

Patients are no longer stored: the details Emma needs are filled in on the
start form and belong to the one chat they were entered for. That moves
`patient_name`, `provider`, `practice` and `recency` onto `Chat`, adds the two
phone numbers the FAQ's placeholders want, and removes the `Conversation`
model along with the `patient_id` columns that pointed at it.

Existing chats predate the form and have nobody to attribute them to, so they
take a blank `patient_name`. Their transcripts are untouched - `Message` is
linked by `conv_id`, not by patient.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("database", "0020_remove_conversation_capture_id_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="chat",
            name="patient_name",
            field=models.CharField(default="", max_length=120),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="chat",
            name="provider",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="chat",
            name="practice",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="chat",
            name="recency",
            field=models.CharField(
                choices=[("onemonth", "onemonth"), ("year", "year")],
                default="year",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="chat",
            name="care_companion_number",
            field=models.CharField(blank=True, max_length=40),
        ),
        migrations.AddField(
            model_name="chat",
            name="practice_phone",
            field=models.CharField(blank=True, max_length=40),
        ),
        migrations.RemoveField(
            model_name="chat",
            name="patient_id",
        ),
        migrations.RemoveField(
            model_name="message",
            name="patient_id",
        ),
        migrations.DeleteModel(
            name="Conversation",
        ),
    ]
