from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.quiz.models import QuizSession


class Command(BaseCommand):
    help = "Terk edilmiş (skoru gönderilmemiş) oturumları siler. Periyodik çalıştırılmalıdır."

    def add_arguments(self, parser):
        parser.add_argument(
            "--max-age-minutes", type=int, default=settings.QUIZ_ABANDONED_AFTER_MINUTES
        )

    def handle(self, *args, max_age_minutes, **options):
        cutoff = timezone.now() - timedelta(minutes=max_age_minutes)
        deleted, _ = QuizSession.objects.filter(
            status__in=[QuizSession.Status.ACTIVE, QuizSession.Status.FINISHED],
            started_at__lt=cutoff,
        ).delete()
        self.stdout.write(f"{deleted} kayıt silindi.")
