from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.categories.models import Category
from apps.questions.models import Choice, Question
from apps.quiz.models import QuizSession

pytestmark = pytest.mark.django_db


def test_health_ok(client):
    resp = client.get("/api/v1/health/")
    assert resp.status_code == 200 and resp.json()["database"] == "up"


def test_openapi_schema_generates(client):
    resp = client.get("/api/v1/schema/")
    assert resp.status_code == 200


def test_seed_questions_import_is_valid_and_idempotent():
    call_command("import_questions", "--seed")
    assert Question.objects.count() == 200
    for cat in Category.objects.all():
        assert Question.objects.filter(category=cat).count() == 40
    for q in Question.objects.prefetch_related("choices"):
        choices = list(q.choices.all())
        assert len(choices) == 4 and sum(c.is_correct for c in choices) == 1
    call_command("import_questions", "--seed")
    assert Question.objects.count() == 200
    # doğru şık konumları çeşitli olmalı
    positions = {
        Choice.objects.filter(question=q, is_correct=True).get().order
        for q in Question.objects.all()[:40]
    }
    assert len(positions) == 4


def test_import_csv(tmp_path):
    f = tmp_path / "q.csv"
    f.write_text(
        "category,text,choice1,choice2,choice3,choice4,correct\n" "fizik,Test sorusu?,a,b,c,d,3\n",
        encoding="utf-8",
    )
    call_command("import_questions", str(f))
    q = Question.objects.get(text="Test sorusu?")
    assert q.choices.get(is_correct=True).text == "c"


def test_cleanup_sessions_removes_only_old_unsubmitted():
    cat = Category.objects.first()
    old_active = QuizSession.objects.create(category=cat)
    fresh = QuizSession.objects.create(category=cat)
    old_submitted = QuizSession.objects.create(category=cat, status="submitted")
    old = timezone.now() - timedelta(hours=2)
    QuizSession.objects.filter(pk__in=[old_active.pk, old_submitted.pk]).update(started_at=old)
    call_command("cleanup_sessions")
    remaining = set(QuizSession.objects.values_list("pk", flat=True))
    assert remaining == {fresh.pk, old_submitted.pk}
