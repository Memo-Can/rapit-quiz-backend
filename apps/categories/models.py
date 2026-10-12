from django.core.validators import RegexValidator
from django.db import models


class Category(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField("ad", max_length=60)
    icon = models.CharField("ikon", max_length=16, blank=True, help_text="Emoji veya ikon adı")
    color = models.CharField(
        "renk",
        max_length=7,
        validators=[RegexValidator(r"^#[0-9A-Fa-f]{6}$", "#RRGGBB biçiminde olmalı.")],
    )
    is_active = models.BooleanField("aktif", default=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "kategori"
        verbose_name_plural = "kategoriler"

    def __str__(self):
        return self.name
