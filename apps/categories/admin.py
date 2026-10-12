from django.contrib import admin

from .models import Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "icon", "color", "is_active")
    list_filter = ("is_active",)
    prepopulated_fields = {"slug": ("name",)}
