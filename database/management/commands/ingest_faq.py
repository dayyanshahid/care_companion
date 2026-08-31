"""Load the Care Companion FAQ into MongoDB as embedded chunks.

Usage:
    python manage.py ingest_faq /path/to/FAQ_Handbook.docx
"""
from django.core.management.base import BaseCommand, CommandError

from api.controllers.knowledge import services


class Command(BaseCommand):
    help = "Parse the FAQ .docx, embed each Q&A with OpenAI, and store it in MongoDB."

    def add_arguments(self, parser):
        parser.add_argument("path", help="Path to the FAQ .docx file")

    def handle(self, *args, **options):
        try:
            count = services.ingest_faq(options["path"])
        except services.KnowledgeError as exc:
            raise CommandError(str(exc))
        self.stdout.write(self.style.SUCCESS(f"Ingested {count} FAQ entries."))
