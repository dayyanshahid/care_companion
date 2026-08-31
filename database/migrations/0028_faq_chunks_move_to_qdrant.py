"""The FAQ moves out of MongoDB and into Qdrant Cloud.

Chunks and their embeddings are now points in a Qdrant collection, so the
`faq_chunks` collection here has nothing left to hold. Re-run `ingest_faq`
after this - it is what fills Qdrant, and nothing is copied across.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("database", "0027_rename_chat_to_remoteenrollement"),
    ]

    operations = [
        migrations.DeleteModel(name="FaqChunk"),
    ]
