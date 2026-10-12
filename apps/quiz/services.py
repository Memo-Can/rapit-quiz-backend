import math
import random
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from apps.core.exceptions import ApiError
from apps.leaderboard.models import ScoreEntry
from apps.questions.models import CHOICES_PER_QUESTION, Choice, Question

from .models import QuizSession, SessionQuestion


def _ms(delta):
    return int(delta.total_seconds() * 1000)


def _lock_session(session_id):
    try:
        return QuizSession.objects.select_for_update().select_related("category").get(pk=session_id)
    except QuizSession.DoesNotExist:
        raise ApiError("session_not_found", "Oyun bulunamadı.", 404)


def _require_active(session):
    if session.status != QuizSession.Status.ACTIVE:
        raise ApiError("session_not_active", "Bu oyun artık aktif değil.", 409)


@transaction.atomic
def start_session(category):
    """Kategoriden rastgele QUIZ_QUESTION_COUNT soru seçip yeni oyun açar."""
    count = settings.QUIZ_QUESTION_COUNT
    valid_ids = list(
        Question.objects.filter(category=category, is_active=True)
        .annotate(
            n_choices=Count("choices"),
            n_correct=Count("choices", filter=Q(choices__is_correct=True)),
        )
        .filter(n_choices=CHOICES_PER_QUESTION, n_correct=1)
        .values_list("id", flat=True)
    )
    if len(valid_ids) < count:
        raise ApiError("not_enough_questions", "Bu kategoride yeterli soru yok.", 503)
    session = QuizSession.objects.create(category=category)
    SessionQuestion.objects.bulk_create(
        SessionQuestion(session=session, question_id=qid, position=pos)
        for pos, qid in enumerate(random.sample(valid_ids, count), start=1)
    )
    return session


def _apply_resolution(session, sq, *, choice, answered_at, elapsed_ms):
    """Bir soruyu sonuçlandırır, oturum toplamlarını günceller, gerekirse oyunu bitirir."""
    limit = settings.QUIZ_TIME_LIMIT_MS
    late = elapsed_ms > limit + settings.QUIZ_NETWORK_TOLERANCE_MS
    is_correct = choice is not None and choice.is_correct and not late

    score = 0
    if is_correct:
        remaining = max(0, limit - elapsed_ms)
        bonus = math.floor(settings.QUIZ_MAX_SPEED_BONUS * remaining / limit + 0.5)
        score = settings.QUIZ_CORRECT_POINTS + bonus
    time_ms = limit if (choice is None or late) else min(elapsed_ms, limit)

    sq.choice = choice
    sq.answered_at = answered_at
    sq.is_correct = is_correct
    sq.score = score
    sq.time_ms = time_ms
    sq.save(update_fields=["choice", "answered_at", "is_correct", "score", "time_ms"])

    session.total_score += score
    session.correct_count += int(is_correct)
    session.total_time_ms += time_ms
    fields = ["total_score", "correct_count", "total_time_ms"]
    if not session.questions.filter(answered_at__isnull=True).exists():
        session.status = QuizSession.Status.FINISHED
        session.finished_at = answered_at
        fields += ["status", "finished_at"]
    session.save(update_fields=fields)
    return is_correct, score


@transaction.atomic
def serve_question(session_id):
    """Sıradaki soruyu verir ve süreyi başlatır.

    Süresi dolmuş soru otomatik olarak süresiz sayılır ve bir sonrakine geçilir.
    Soru kalmadıysa None döner (oyun bitmiştir).
    Dönüş: (SessionQuestion, remaining_ms) | None
    """
    session = _lock_session(session_id)
    _require_active(session)
    now = timezone.now()
    limit_ms = settings.QUIZ_TIME_LIMIT_MS

    pending = (
        session.questions.select_related("question")
        .prefetch_related("question__choices")
        .filter(answered_at__isnull=True)
    )
    for sq in pending:
        if sq.served_at is None:
            sq.served_at = now
            sq.save(update_fields=["served_at"])
            return sq, limit_ms
        elapsed = _ms(now - sq.served_at)
        if elapsed < limit_ms:
            return sq, limit_ms - elapsed
        _apply_resolution(
            session,
            sq,
            choice=None,
            answered_at=sq.served_at + timedelta(milliseconds=limit_ms),
            elapsed_ms=limit_ms,
        )
    return None


@transaction.atomic
def submit_answer(session_id, position, choice_id):
    session = _lock_session(session_id)
    _require_active(session)

    try:
        sq = session.questions.select_related("question").get(position=position)
    except SessionQuestion.DoesNotExist:
        raise ApiError("question_not_found", "Böyle bir soru yok.", 404)
    if sq.answered_at is not None:
        raise ApiError("already_answered", "Bu soru zaten cevaplandı.", 409)
    if sq.served_at is None:
        raise ApiError("question_not_served", "Bu soru henüz istenmedi.", 409)

    choice = None
    if choice_id is not None:
        choice = Choice.objects.filter(pk=choice_id, question_id=sq.question_id).first()
        if choice is None:
            raise ApiError("invalid_choice", "Şık bu soruya ait değil.", 400)

    now = timezone.now()
    is_correct, score = _apply_resolution(
        session, sq, choice=choice, answered_at=now, elapsed_ms=_ms(now - sq.served_at)
    )
    correct_choice_id = (
        Choice.objects.filter(question_id=sq.question_id, is_correct=True)
        .values_list("id", flat=True)
        .get()
    )
    return {
        "is_correct": is_correct,
        "correct_choice_id": correct_choice_id,
        "score_gained": score,
        "finished": session.status == QuizSession.Status.FINISHED,
    }


def get_result(session_id):
    try:
        session = QuizSession.objects.select_related("category").get(pk=session_id)
    except QuizSession.DoesNotExist:
        raise ApiError("session_not_found", "Oyun bulunamadı.", 404)
    if session.status == QuizSession.Status.ACTIVE:
        raise ApiError("session_not_finished", "Oyun henüz bitmedi.", 409)
    return {
        "category": session.category.slug,
        "total_score": session.total_score,
        "correct_count": session.correct_count,
        "question_count": settings.QUIZ_QUESTION_COUNT,
        "total_time_ms": session.total_time_ms,
        "score_submitted": session.status == QuizSession.Status.SUBMITTED,
    }


def rank_of(entry):
    """Eşitlik kuralıyla (puan, süre, kayıt zamanı) kaydın kategorideki sırası."""
    better = (
        Q(score__gt=entry.score)
        | Q(score=entry.score, total_time_ms__lt=entry.total_time_ms)
        | Q(
            score=entry.score,
            total_time_ms=entry.total_time_ms,
            created_at__lte=entry.created_at,
        )
    )
    return (
        ScoreEntry.objects.filter(category_id=entry.category_id)
        .filter(better)
        .exclude(pk=entry.pk)
        .count()
        + 1
    )


@transaction.atomic
def submit_score(session_id, player_name):
    session = _lock_session(session_id)
    if session.status == QuizSession.Status.SUBMITTED:
        raise ApiError("already_submitted", "Bu oyunun skoru zaten gönderildi.", 409)
    if session.status != QuizSession.Status.FINISHED:
        raise ApiError("session_not_finished", "Oyun henüz bitmedi.", 409)

    entry = ScoreEntry.objects.create(
        session=session,
        category=session.category,
        player_name=player_name,
        score=session.total_score,
        correct_count=session.correct_count,
        total_time_ms=session.total_time_ms,
    )
    session.status = QuizSession.Status.SUBMITTED
    session.save(update_fields=["status"])
    return entry, rank_of(entry)
