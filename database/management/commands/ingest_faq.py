"""Load the Care Companion FAQ into MongoDB as embedded chunks.

Usage:
    python manage.py ingest_faq /path/to/FAQ_Handbook.docx
"""
from django.core.management.base import BaseCommand, CommandError

from api.controllers.knowledge import services
from utils.messages import messages


class Command(BaseCommand):
    help = messages["ingestCommandHelp"]

    def add_arguments(self, parser):
        parser.add_argument("path", help=messages["ingestPathHelp"])

    def handle(self, *args, **options):
        try:
            count = services.ingest_faq(options["path"])
        except services.KnowledgeError as exc:
            raise CommandError(str(exc))
        self.stdout.write(self.style.SUCCESS(messages["ingestSuccess"].format(count=count)))
