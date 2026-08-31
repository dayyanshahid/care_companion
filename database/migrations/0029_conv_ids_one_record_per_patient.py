"""One `remoteenrollement` document per patient, holding every conversation.

Until now a second chat with the same patient wrote a second document -
same name, same profile, only a different `conv_id` - and split their
transcript across the two. `conv_id` becomes `conv_ids`, an array of every
OpenAI conversation ever opened with that patient, and the duplicates are
folded into the one record they should always have been.

Folding a patient's documents together keeps the oldest as their record,
because that is when they were first captured. Their conversation ids are
collected onto it in the order they were opened, and the details Emma reads -
profile, provider, practice, status - are taken from the newest document,
which holds the freshest copy. Every message on a duplicate is repointed at
the surviving record, so a patient's whole transcript hangs off one id.

Documents with no `patient_id` cannot be grouped by patient, so each keeps
its own record and simply gains a one-element `conv_ids`.

Reversing this restores `conv_id` from the newest conversation on each
record. It cannot split a merged record back into several - those documents
are gone.
"""
from django.db import migrations, models

import django_mongodb_backend.fields.array


def fold_onto_one_record(apps, schema_editor):
    RemoteEnrollement = apps.get_model("database", "RemoteEnrollement")
    Message = apps.get_model("database", "Message")

    by_patient = {}
    loose = []

    for chat in RemoteEnrollement.objects.all().order_by("created_at"):
        if chat.patient_id is None:
            loose.append(chat)
        else:
            by_patient.setdefault(str(chat.patient_id), []).append(chat)

    for chat in loose:
        RemoteEnrollement.objects.filter(pk=chat.pk).update(
            conv_ids=[chat.conv_id] if chat.conv_id else []
        )

    for chats in by_patient.values():
        keeper, duplicates = chats[0], chats[1:]
        newest = chats[-1]

        conv_ids = []

        for chat in chats:
            if chat.conv_id and chat.conv_id not in conv_ids:
                conv_ids.append(chat.conv_id)

        RemoteEnrollement.objects.filter(pk=keeper.pk).update(
            conv_ids=conv_ids,
            patient_profile=newest.patient_profile,
            patient_name=newest.patient_name,
            provider=newest.provider,
            practice=newest.practice,
            recency=newest.recency,
            status=newest.status,
        )

        for chat in duplicates:
            Message.objects.filter(remoteenrollement_id=chat.pk).update(
                remoteenrollement_id=keeper.pk
            )
            chat.delete()

        # Messages written before the id was carried, matched by the
        # conversation they name.
        if conv_ids:
            Message.objects.filter(
                conversation_id__in=conv_ids, remoteenrollement_id=None
            ).update(remoteenrollement_id=keeper.pk)


def restore_single_conv_id(apps, schema_editor):
    """Put back the newest conversation as the record's `conv_id`."""
    RemoteEnrollement = apps.get_model("database", "RemoteEnrollement")

    for chat in RemoteEnrollement.objects.all():
        conv_ids = chat.conv_ids or []

        RemoteEnrollement.objects.filter(pk=chat.pk).update(
            conv_id=conv_ids[-1] if conv_ids else ""
        )


class Migration(migrations.Migration):

    dependencies = [
        ("database", "0028_faq_chunks_move_to_qdrant"),
    ]

    operations = [
        migrations.AddField(
            model_name="remoteenrollement",
            name="conv_ids",
            field=django_mongodb_backend.fields.array.ArrayField(
                models.CharField(max_length=255),
                blank=True,
                db_index=True,
                default=list,
                size=None,
            ),
        ),
        migrations.RunPython(fold_onto_one_record, restore_single_conv_id),
        migrations.RemoveField(
            model_name="remoteenrollement",
            name="conv_id",
        ),
    ]
