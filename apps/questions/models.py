from django.db import models

CHOICES_PER_QUESTION = 4


class Question(models.Model):
    category = models.ForeignKey(
        "categories.Category",
        on_delete=models.CASCADE,
        related_name="questions",
        verbose_name="kategori",
    )
    text = models.TextField("soru metni")
    is_active = models.BooleanField("aktif", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "soru"
        verbose_name_plural = "sorular"

    def __str__(self):
        return self.text[:80]


class Choice(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="choices", verbose_name="soru"
    )
    text = models.CharField("şık", max_length=200)
    is_correct = models.BooleanField("doğru cevap", default=False)
    order = models.PositiveSmallIntegerField("sıra", default=0)

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["question", "order"], name="uniq_choice_order"),
        ]
        verbose_name = "şık"
        verbose_name_plural = "şıklar"

    def __str__(self):
        return self.text
