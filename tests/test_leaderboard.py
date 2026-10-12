import pytest

from apps.leaderboard.models import ScoreEntry
from apps.leaderboard.profanity import is_inappropriate

from .conftest import play_all

pytestmark = pytest.mark.django_db


def submit(client, sid, name):
    return client.post(
        f"/api/v1/sessions/{sid}/submit-score/", {"player_name": name}, format="json"
    )


def finished_game(client, start_game, clock, **kwargs):
    sid = start_game()
    play_all(client, sid, clock, **kwargs)
    return sid


def test_submit_score_and_leaderboard(client, start_game, clock):
    sid = finished_game(client, start_game, clock, answer_ms=0)
    resp = submit(client, sid, "  Ayşe   Nur ")
    assert resp.status_code == 201
    body = resp.json()
    assert body["player_name"] == "Ayşe Nur" and body["rank"] == 1 and body["score"] == 3000

    board = client.get("/api/v1/leaderboard/?category=yazilim").json()
    assert len(board) == 1
    assert board[0]["entry_id"] == body["entry_id"] and board[0]["rank"] == 1
    assert client.get(f"/api/v1/sessions/{sid}/result/").json()["score_submitted"] is True


def test_submit_only_once(client, start_game, clock):
    sid = finished_game(client, start_game, clock)
    assert submit(client, sid, "Ali").status_code == 201
    again = submit(client, sid, "Ali")
    assert again.status_code == 409 and again.json()["error"]["code"] == "already_submitted"
    assert ScoreEntry.objects.count() == 1


def test_submit_requires_finished_game(client, start_game):
    sid = start_game()
    resp = submit(client, sid, "Ali")
    assert resp.status_code == 409 and resp.json()["error"]["code"] == "session_not_finished"


@pytest.mark.parametrize("name", ["A", "x" * 21, "   ", ""])
def test_invalid_names(client, start_game, clock, name):
    sid = finished_game(client, start_game, clock)
    assert submit(client, sid, name).status_code == 400
    # başarısız deneme oyunu tüketmez
    assert submit(client, sid, "Geçerli").status_code == 201


def test_profane_name_rejected(client, start_game, clock):
    sid = finished_game(client, start_game, clock)
    resp = submit(client, sid, "s1ktir")
    assert resp.status_code == 400 and resp.json()["error"]["code"] == "inappropriate_name"


def test_profanity_filter_avoids_false_positives():
    assert is_inappropriate("AMK")
    assert is_inappropriate("f.u.c.k")
    assert not is_inappropriate("Sıla")
    assert not is_inappropriate("Ocak")
    assert not is_inappropriate("Gotham")


def test_ranking_and_tiebreaks(client, start_game, clock):
    fast = finished_game(client, start_game, clock, answer_ms=500)
    slow = finished_game(client, start_game, clock, answer_ms=1500)
    wrong = finished_game(client, start_game, clock, answer_ms=100, correct=False)
    # önce yavaş olanı kaydet: yine de puanı düşük olduğu için 2. olmalı
    s = submit(client, slow, "Yavaş").json()
    assert s["rank"] == 1
    f = submit(client, fast, "Hızlı").json()
    assert f["rank"] == 1
    w = submit(client, wrong, "Yanlış").json()
    assert w["rank"] == 3
    names = [e["player_name"] for e in client.get("/api/v1/leaderboard/?category=yazilim").json()]
    assert names == ["Hızlı", "Yavaş", "Yanlış"]


def test_same_score_same_time_earlier_entry_first(client, start_game, clock):
    a = finished_game(client, start_game, clock, answer_ms=1000)
    b = finished_game(client, start_game, clock, answer_ms=1000)
    assert submit(client, a, "Birinci").json()["rank"] == 1
    assert submit(client, b, "İkinci").json()["rank"] == 2
    names = [e["player_name"] for e in client.get("/api/v1/leaderboard/?category=yazilim").json()]
    assert names == ["Birinci", "İkinci"]


def test_duplicate_names_allowed(client, start_game, clock):
    for _ in range(2):
        assert submit(client, finished_game(client, start_game, clock), "Aynı").status_code == 201


def test_leaderboard_limit_and_validation(client, start_game, clock, category):
    for i in range(12):
        submit(client, finished_game(client, start_game, clock), f"Oyuncu{i}")
    assert len(client.get("/api/v1/leaderboard/?category=yazilim").json()) == 10
    assert len(client.get("/api/v1/leaderboard/?category=yazilim&limit=3").json()) == 3
    assert len(client.get("/api/v1/leaderboard/?category=yazilim&limit=500").json()) == 12
    assert client.get("/api/v1/leaderboard/").json()["error"]["code"] == "category_required"
    assert client.get("/api/v1/leaderboard/?category=yok").status_code == 404
    assert client.get("/api/v1/leaderboard/?category=yazilim&limit=x").status_code == 400


def test_leaderboard_is_per_category(client, start_game, clock):
    submit(client, finished_game(client, start_game, clock), "Ali")
    assert client.get("/api/v1/leaderboard/?category=fizik").json() == []


def test_throttling(client, category, settings):
    settings.THROTTLE_SESSION_START = "2/min"
    codes = [
        client.post("/api/v1/sessions/", {"category": "yazilim"}, format="json").status_code
        for _ in range(3)
    ]
    assert codes == [201, 201, 429]
    resp = client.post("/api/v1/sessions/", {"category": "yazilim"}, format="json")
    assert resp.json()["error"]["code"] == "throttled"
