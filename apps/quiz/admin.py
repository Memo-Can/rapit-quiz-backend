from django.contrib import admin

from .models import QuizSession


@admin.register(QuizSession)
class QuizSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "category", "status", "total_score", "correct_count", "started_at")
    list_filter = ("status", "category")
    readonly_fields = [f.name for f in QuizSession._meta.fields]

    def has_add_permission(self, request):
        return False
