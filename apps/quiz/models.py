import uuid

from django.db import models


class QuizSession(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Aktif"
        FINISHED = "finished", "Bitti"
        SUBMITTED = "submitted", "Skor gönderildi"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(
        "categories.Category", on_delete=models.PROTECT, related_name="sessions"
    )
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    total_score = models.PositiveIntegerField(default=0)
    correct_count = models.PositiveSmallIntegerField(default=0)
    total_time_ms = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-started_at"]
        indexes = [models.Index(fields=["status", "started_at"])]

    def __str__(self):
        return f"{self.id} ({self.status})"


class SessionQuestion(models.Model):
    session = models.ForeignKey(QuizSession, on_delete=models.CASCADE, related_name="questions")
    question = models.ForeignKey("questions.Question", on_delete=models.PROTECT, related_name="+")
    position = models.PositiveSmallIntegerField()
    served_at = models.DateTimeField(null=True, blank=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    choice = models.ForeignKey(
        "questions.Choice", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    is_correct = models.BooleanField(default=False)
    score = models.PositiveSmallIntegerField(default=0)
    # Bu soruya harcanan süre; cevapsız/süresi dolan sorularda süre sınırına eşittir.
    time_ms = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(fields=["session", "position"], name="uniq_session_position"),
            models.UniqueConstraint(fields=["session", "question"], name="uniq_session_question"),
        ]

    def __str__(self):
        return f"{self.session_id}#{self.position}"
