import csv
import json
import random
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.categories.models import Category
from apps.questions.models import CHOICES_PER_QUESTION, Choice, Question

SEED_DIR = Path(__file__).resolve().parents[2] / "seed_data"


def normalize_item(item, default_category=None):
    """Satırı {category, text, choices[4], correct(0-3)} biçimine çevirir.

    JSON biçimleri:
      tam:     {"category", "text", "choices": [4 şık], "correct": 0-3}
      kompakt: {"category", "q", "a": doğru şık, "w": [3 yanlış şık]}  (şıklar karıştırılır)
    """
    category = item.get("category") or default_category
    if "q" in item:
        text, choices = item["q"], [item["a"], *item["w"]]
        random.Random(text).shuffle(choices)  # soru metnine bağlı, tekrarlanabilir karışım
        correct = choices.index(item["a"])
    else:
        text, choices, correct = item["text"], list(item["choices"]), int(item["correct"])
    text = str(text).strip()
    choices = [str(c).strip() for c in choices]
    if not category:
        raise ValueError("kategori yok")
    if not text:
        raise ValueError("soru metni boş")
    if len(choices) != CHOICES_PER_QUESTION or len(set(choices)) != CHOICES_PER_QUESTION:
        raise ValueError(f"{CHOICES_PER_QUESTION} farklı şık olmalı")
    if not 0 <= correct < CHOICES_PER_QUESTION:
        raise ValueError("correct 0-3 arasında olmalı")
    return {"category": category, "text": text, "choices": choices, "correct": correct}


def read_file(path, default_category):
    if path.suffix == ".json":
        items = json.loads(path.read_text(encoding="utf-8"))
        return [normalize_item(i, default_category) for i in items]
    if path.suffix == ".csv":
        # category,text,choice1,choice2,choice3,choice4,correct(1-4)
        rows = []
        with path.open(encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                rows.append(
                    normalize_item(
                        {
                            "category": r.get("category") or default_category,
                            "text": r["text"],
                            "choices": [r[f"choice{i}"] for i in range(1, 5)],
                            "correct": int(r["correct"]) - 1,
                        }
                    )
                )
        return rows
    raise CommandError(f"Desteklenmeyen dosya türü: {path.suffix} (.json veya .csv)")


class Command(BaseCommand):
    help = "Soruları JSON/CSV dosyasından içe aktarır. Aynı metne sahip sorular atlanır."

    def add_arguments(self, parser):
        parser.add_argument("files", nargs="*", type=Path)
        parser.add_argument(
            "--seed", action="store_true", help="Depodaki başlangıç sorularını yükle"
        )
        parser.add_argument("--category", help="Dosyada kategori yoksa kullanılacak slug")
        parser.add_argument("--dry-run", action="store_true")

    @transaction.atomic
    def handle(self, *args, files, seed, category, dry_run, **options):
        if seed:
            files = [*files, *sorted(SEED_DIR.glob("*.json"))]
        if not files:
            raise CommandError("Dosya verilmedi (veya --seed kullanın).")

        categories = {c.slug: c for c in Category.objects.all()}
        created = skipped = 0
        for path in files:
            default = category or (path.stem if path.stem in categories else None)
            try:
                rows = read_file(path, default)
            except (ValueError, KeyError) as exc:
                raise CommandError(f"{path.name}: {exc!r}")
            for n, row in enumerate(rows, start=1):
                cat = categories.get(row["category"])
                if cat is None:
                    raise CommandError(f"{path.name} #{n}: bilinmeyen kategori {row['category']!r}")
                if Question.objects.filter(category=cat, text=row["text"]).exists():
                    skipped += 1
                    continue
                question = Question.objects.create(category=cat, text=row["text"])
                Choice.objects.bulk_create(
                    Choice(question=question, text=t, is_correct=(i == row["correct"]), order=i)
                    for i, t in enumerate(row["choices"])
                )
                created += 1
        if dry_run:
            transaction.set_rollback(True)
        self.stdout.write(
            self.style.SUCCESS(
                f"{created} soru eklendi, {skipped} atlandı" + (" (dry-run)" if dry_run else "")
            )
        )
