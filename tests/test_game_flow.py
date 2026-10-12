import pytest

from apps.questions.models import Choice
from apps.quiz.models import QuizSession, SessionQuestion

from .conftest import correct_choice_id, get_question, play_all

pytestmark = pytest.mark.django_db


def answer(client, sid, pos, choice_id):
    return client.post(
        f"/api/v1/sessions/{sid}/answer/",
        {"question_position": pos, "choice_id": choice_id},
        format="json",
    )


def test_categories_listed(client, category):
    resp = client.get("/api/v1/categories/")
    assert resp.status_code == 200
    slugs = [c["slug"] for c in resp.json()]
    assert slugs == [
        "yazilim",
        "yapay-zeka",
        "bilgisayar-muhendisligi",
        "ulkeler",
        "fizik",
    ]
    assert set(resp.json()[0]) == {"id", "slug", "name", "icon", "color"}


def test_start_session_assigns_20_distinct_questions(client, start_game):
    sid = start_game()
    sqs = SessionQuestion.objects.filter(session_id=sid)
    assert sqs.count() == 20
    assert sqs.values("question_id").distinct().count() == 20
    assert sorted(sqs.values_list("position", flat=True)) == list(range(1, 21))


def test_start_unknown_category(client, db):
    resp = client.post("/api/v1/sessions/", {"category": "yok"}, format="json")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "category_not_found"


def test_start_not_enough_questions(client, db):
    resp = client.post("/api/v1/sessions/", {"category": "fizik"}, format="json")
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "not_enough_questions"


def test_question_hides_correct_answer(client, start_game):
    sid = start_game()
    body = get_question(client, sid).json()
    assert body["position"] == 1
    assert body["time_limit_ms"] == 5000
    assert len(body["choices"]) == 4
    assert all(set(c) == {"id", "text"} for c in body["choices"])


def test_question_is_not_advanced_until_answered(client, start_game, clock):
    sid = start_game()
    first = get_question(client, sid).json()
    clock.advance(1200)
    again = get_question(client, sid).json()
    assert again["position"] == 1 and again["text"] == first["text"]
    assert again["remaining_ms"] == 3800  # served_at sıfırlanmaz


def test_perfect_game_scores(client, start_game, clock):
    sid = start_game()
    last = play_all(client, sid, clock, answer_ms=0)
    assert last.json()["finished"] is True
    result = client.get(f"/api/v1/sessions/{sid}/result/").json()
    assert result["total_score"] == 20 * 150
    assert result["correct_count"] == 20
    assert result["score_submitted"] is False


def test_speed_bonus_formula(client, start_game, clock):
    sid = start_game()
    q = get_question(client, sid)
    clock.advance(2000)  # kalan 3000 ms -> bonus round(50*3000/5000)=30
    resp = answer(client, sid, 1, correct_choice_id(q))
    body = resp.json()
    assert body["is_correct"] is True
    assert body["score_gained"] == 130
    assert body["finished"] is False
    assert Choice.objects.get(pk=body["correct_choice_id"]).is_correct


def test_wrong_answer_zero_points(client, start_game, clock):
    sid = start_game()
    q = get_question(client, sid)
    wrong = Choice.objects.filter(question__text=q.json()["text"], is_correct=False).first()
    clock.advance(500)
    body = answer(client, sid, 1, wrong.id).json()
    assert body["is_correct"] is False and body["score_gained"] == 0


def test_answer_within_tolerance_gets_no_bonus(client, start_game, clock):
    sid = start_game()
    q = get_question(client, sid)
    clock.advance(5500)  # 5000 < 5500 <= 5700
    body = answer(client, sid, 1, correct_choice_id(q)).json()
    assert body["is_correct"] is True and body["score_gained"] == 100


def test_late_answer_is_timed_out(client, start_game, clock):
    sid = start_game()
    q = get_question(client, sid)
    clock.advance(5800)
    body = answer(client, sid, 1, correct_choice_id(q)).json()
    assert body["is_correct"] is False and body["score_gained"] == 0
    assert "correct_choice_id" in body


def test_null_choice_counts_as_timeout(client, start_game, clock):
    sid = start_game()
    get_question(client, sid)
    clock.advance(5000)
    body = answer(client, sid, 1, None).json()
    assert body["is_correct"] is False and body["score_gained"] == 0
    assert QuizSession.objects.get(pk=sid).total_time_ms == 5000


def test_cannot_answer_twice(client, start_game, clock):
    sid = start_game()
    q = get_question(client, sid)
    choice = correct_choice_id(q)
    assert answer(client, sid, 1, choice).status_code == 200
    again = answer(client, sid, 1, choice)
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "already_answered"


def test_cannot_answer_unserved_question(client, start_game):
    sid = start_game()
    resp = answer(client, sid, 3, None)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "question_not_served"


def test_choice_must_belong_to_question(client, start_game):
    sid = start_game()
    q = get_question(client, sid)
    other = Choice.objects.exclude(question__text=q.json()["text"]).first()
    resp = answer(client, sid, 1, other.id)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "invalid_choice"


def test_expired_question_is_auto_closed_on_next_request(client, start_game, clock):
    sid = start_game()
    get_question(client, sid)
    clock.advance(6000)
    nxt = get_question(client, sid).json()
    assert nxt["position"] == 2 and nxt["remaining_ms"] == 5000
    first = SessionQuestion.objects.get(session_id=sid, position=1)
    assert first.answered_at is not None and first.score == 0 and first.choice is None
    # otomatik kapanan soru artık cevaplanamaz
    assert answer(client, sid, 1, None).status_code == 409


def test_all_timeouts_finish_the_game(client, start_game, clock):
    sid = start_game()
    for _ in range(20):
        get_question(client, sid)
        clock.advance(6000)
    resp = get_question(client, sid)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "session_finished"
    session = QuizSession.objects.get(pk=sid)
    assert session.status == "finished" and session.total_score == 0
    assert session.total_time_ms == 20 * 5000


def test_result_requires_finished_game(client, start_game):
    sid = start_game()
    resp = client.get(f"/api/v1/sessions/{sid}/result/")
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "session_not_finished"


def test_finished_session_rejects_more_questions(client, start_game, clock):
    sid = start_game()
    play_all(client, sid, clock)
    resp = get_question(client, sid)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "session_not_active"


def test_unknown_session_is_json_404(client, db):
    resp = client.get("/api/v1/sessions/3f6b2d0e-0000-4000-8000-000000000000/question/")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "session_not_found"
    bad = client.get("/api/v1/sessions/not-a-uuid/question/")
    assert bad.status_code == 404 and bad.json()["error"]["code"] == "not_found"
