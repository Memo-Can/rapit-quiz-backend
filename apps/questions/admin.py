from django import forms
from django.contrib import admin

from .models import CHOICES_PER_QUESTION, Choice, Question


class ChoiceInlineFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        forms_ = [
            f for f in self.forms if f.cleaned_data and not f.cleaned_data.get("DELETE", False)
        ]
        if len(forms_) != CHOICES_PER_QUESTION:
            raise forms.ValidationError(f"Her sorunun tam {CHOICES_PER_QUESTION} şıkkı olmalı.")
        correct = sum(1 for f in forms_ if f.cleaned_data.get("is_correct"))
        if correct != 1:
            raise forms.ValidationError("Her sorunun tam 1 doğru şıkkı olmalı.")


class ChoiceInline(admin.TabularInline):
    model = Choice
    formset = ChoiceInlineFormSet
    extra = 0
    min_num = CHOICES_PER_QUESTION
    max_num = CHOICES_PER_QUESTION
    validate_min = True
    can_delete = False


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("text", "category", "is_active", "created_at")
    list_filter = ("category", "is_active")
    search_fields = ("text",)
    inlines = [ChoiceInline]
