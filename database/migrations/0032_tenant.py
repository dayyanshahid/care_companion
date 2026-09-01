from django.db import migrations, models

# Everything written before this migration was written while the service
# served one practice, and that practice was Prime Care Health.
FIRST_TENANT = "primecare"


def stamp_first_tenant(apps, schema_editor):
    """Give the records that predate multi-tenancy the tenant they were for.

    Without this they would match no tenant at all, and every chat opened so
    far would read as missing.
    """
    for name in ("RemoteEnrollement", "Message"):
        apps.get_model("database", name).objects.filter(tenant="").update(
            tenant=FIRST_TENANT
        )


class Migration(migrations.Migration):

    dependencies = [
        ("database", "0031_remove_callback_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="remoteenrollement",
            name="tenant",
            field=models.CharField(db_index=True, default="", max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="message",
            name="tenant",
            field=models.CharField(db_index=True, default="", max_length=100),
            preserve_default=False,
        ),
        migrations.RunPython(stamp_first_tenant, migrations.RunPython.noop),
    ]
