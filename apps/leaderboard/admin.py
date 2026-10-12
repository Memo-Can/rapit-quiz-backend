from django.contrib import admin

from .models import ScoreEntry


@admin.register(ScoreEntry)
class ScoreEntryAdmin(admin.ModelAdmin):
    list_display = (
        "player_name",
        "category",
        "score",
        "correct_count",
        "total_time_ms",
        "created_at",
    )
    list_filter = ("category",)
    search_fields = ("player_name",)
