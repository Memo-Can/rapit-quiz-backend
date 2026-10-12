from datetime import datetime, timedelta, timezone

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.categories.models import Category
from apps.questions.models import Choice, Question

START = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


class Clock:
    """timezone.now() için ayarlanabilir sahte saat."""

    def __init__(self):
        self.current = START

    def advance(self, ms):
        self.current += timedelta(milliseconds=ms)


@pytest.fixture
def clock(monkeypatch):
    c = Clock()
    monkeypatch.setattr("django.utils.timezone.now", lambda: c.current)
    return c


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()


@pytest.fixture
def client():
    return APIClient()


def make_questions(category, n, prefix="Soru"):
    for i in range(n):
        q = Question.objects.create(category=category, text=f"{prefix} {category.slug} {i}")
        for order in range(4):
            Choice.objects.create(
                question=q, text=f"Şık {order}", is_correct=(order == 0), order=order
            )


@pytest.fixture
def category(db):
    # 0002 migrasyonu kategorileri zaten oluşturur
    cat = Category.objects.get(slug="yazilim")
    make_questions(cat, 25)
    return cat


@pytest.fixture
def start_game(client, category):
    def _start():
        resp = client.post("/api/v1/sessions/", {"category": category.slug}, format="json")
        assert resp.status_code == 201, resp.content
        return resp.json()["session_id"]

    return _start


def get_question(client, sid):
    return client.get(f"/api/v1/sessions/{sid}/question/")


def correct_choice_id(position_text_resp):
    """Testlerde doğru şıkkı DB'den bulur (API doğru cevabı vermez)."""
    texts = position_text_resp.json()["text"]
    return Choice.objects.get(question__text=texts, is_correct=True).id


def play_all(client, sid, clock, *, answer_ms=1000, correct=True):
    last = None
    for pos in range(1, 21):
        q = get_question(client, sid)
        assert q.status_code == 200, q.content
        assert q.json()["position"] == pos
        clock.advance(answer_ms)
        if correct:
            choice = correct_choice_id(q)
        else:
            choice = (
                Choice.objects.filter(question__text=q.json()["text"], is_correct=False).first().id
            )
        last = client.post(
            f"/api/v1/sessions/{sid}/answer/",
            {"question_position": pos, "choice_id": choice},
            format="json",
        )
        assert last.status_code == 200, last.content
    return last
