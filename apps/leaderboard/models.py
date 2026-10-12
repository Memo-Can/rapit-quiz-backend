from django.db import models


class ScoreEntry(models.Model):
    session = models.OneToOneField(
        "quiz.QuizSession", on_delete=models.CASCADE, related_name="score_entry"
    )
    category = models.ForeignKey(
        "categories.Category", on_delete=models.CASCADE, related_name="score_entries"
    )
    player_name = models.CharField("oyuncu", max_length=20)
    score = models.PositiveIntegerField()
    correct_count = models.PositiveSmallIntegerField()
    total_time_ms = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Eşitlikte: kısa süre, sonra önce kaydedilen.
        ordering = ["-score", "total_time_ms", "created_at", "id"]
        indexes = [
            models.Index(fields=["category", "-score", "total_time_ms", "created_at"]),
        ]
        verbose_name = "skor"
        verbose_name_plural = "skorlar"

    def __str__(self):
        return f"{self.player_name}: {self.score}"
