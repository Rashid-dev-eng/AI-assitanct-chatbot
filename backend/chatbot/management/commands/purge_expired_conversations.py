from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from chatbot.models import Conversation


class Command(BaseCommand):
    help = "Delete chatbot conversations older than CHAT_RETENTION_DAYS (including their messages and feedback)."

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=settings.CHAT_RETENTION_DAYS)
        deleted, _ = Conversation.objects.filter(updated_at__lt=cutoff).delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} expired chatbot records."))
