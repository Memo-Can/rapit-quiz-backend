from django.db import migrations

CATEGORIES = [
    ("yazilim", "Yazılım", "💻", "#6C5CE7"),
    ("yapay-zeka", "Yapay Zeka", "🤖", "#00B8A9"),
    ("bilgisayar-muhendisligi", "Bilgisayar Mühendisliği", "🖥️", "#FF6B81"),
    ("ulkeler", "Ülkeler", "🌍", "#F5B820"),
    ("fizik", "Fizik", "⚛️", "#FF9F43"),
]


def create_categories(apps, schema_editor):
    Category = apps.get_model("categories", "Category")
    for slug, name, icon, color in CATEGORIES:
        Category.objects.get_or_create(
            slug=slug, defaults={"name": name, "icon": icon, "color": color}
        )


class Migration(migrations.Migration):
    dependencies = [("categories", "0001_initial")]
    operations = [migrations.RunPython(create_categories, migrations.RunPython.noop)]
