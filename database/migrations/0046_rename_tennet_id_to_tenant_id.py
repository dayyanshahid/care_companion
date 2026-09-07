"""`tennet_id` was a misspelling. The field is the tenant's id, so name it that.

Renaming keeps every stored value; only the key changes.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("database", "0045_promptfile_tennet_id_alter_systemprompt_tennet_id"),
    ]

    operations = [
        migrations.RenameField(
            model_name="systemprompt",
            old_name="tennet_id",
            new_name="tenant_id",
        ),
        migrations.RenameField(
            model_name="promptfile",
            old_name="tennet_id",
            new_name="tenant_id",
        ),
    ]
