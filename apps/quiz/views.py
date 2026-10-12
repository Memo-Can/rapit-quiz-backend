from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.categories.models import Category
from apps.core.exceptions import ApiError
from apps.core.throttles import ScoreSubmitThrottle, SessionStartThrottle
from apps.leaderboard.profanity import is_inappropriate

from . import services
from .serializers import (
    AnswerInSerializer,
    AnswerOutSerializer,
    QuestionOutSerializer,
    ResultSerializer,
    SessionCreatedSerializer,
    StartSessionSerializer,
    SubmitScoreInSerializer,
    SubmitScoreOutSerializer,
)

PLAYER_NAME_MIN = 2
PLAYER_NAME_MAX = 20


class SessionCreateView(APIView):
    throttle_classes = [SessionStartThrottle]

    @extend_schema(
        summary="Yeni oyun başlat (20 soru atanır)",
        request=StartSessionSerializer,
        responses={201: SessionCreatedSerializer},
    )
    def post(self, request):
        serializer = StartSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            category = Category.objects.get(
                slug=serializer.validated_data["category"], is_active=True
            )
        except Category.DoesNotExist:
            raise ApiError("category_not_found", "Kategori bulunamadı.", 404)
        session = services.start_session(category)
        data = {
            "session_id": session.id,
            "category": category.slug,
            "question_count": settings.QUIZ_QUESTION_COUNT,
        }
        return Response(SessionCreatedSerializer(data).data, status=status.HTTP_201_CREATED)


class QuestionView(APIView):
    @extend_schema(
        summary="Sıradaki soruyu ver ve süreyi başlat",
        description=(
            "Doğru cevap dönmez. Mevcut soru cevaplanmadıysa ve süresi dolmadıysa aynı soru "
            "kalan süreyle tekrar döner. Süresi dolan soru otomatik süresiz sayılır. "
            "Soru kalmadıysa 409 `session_finished`."
        ),
        responses={200: QuestionOutSerializer},
    )
    def get(self, request, session_id):
        served = services.serve_question(session_id)
        if served is None:
            raise ApiError("session_finished", "Oyun bitti; sonucu alabilirsiniz.", 409)
        sq, remaining_ms = served
        data = {
            "position": sq.position,
            "total_questions": settings.QUIZ_QUESTION_COUNT,
            "text": sq.question.text,
            "choices": [{"id": c.id, "text": c.text} for c in sq.question.choices.all()],
            "time_limit_ms": settings.QUIZ_TIME_LIMIT_MS,
            "remaining_ms": remaining_ms,
        }
        return Response(QuestionOutSerializer(data).data)


class AnswerView(APIView):
    @extend_schema(
        summary="Soruyu cevapla",
        request=AnswerInSerializer,
        responses={200: AnswerOutSerializer},
    )
    def post(self, request, session_id):
        serializer = AnswerInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = services.submit_answer(
            session_id,
            serializer.validated_data["question_position"],
            serializer.validated_data["choice_id"],
        )
        return Response(AnswerOutSerializer(result).data)


class ResultView(APIView):
    @extend_schema(summary="Oyun sonucu", responses={200: ResultSerializer})
    def get(self, request, session_id):
        return Response(ResultSerializer(services.get_result(session_id)).data)


class SubmitScoreView(APIView):
    throttle_classes = [ScoreSubmitThrottle]

    @extend_schema(
        summary="Skoru skor tablosuna yaz (oyun başına bir kez)",
        request=SubmitScoreInSerializer,
        responses={201: SubmitScoreOutSerializer},
    )
    def post(self, request, session_id):
        serializer = SubmitScoreInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        name = " ".join(serializer.validated_data["player_name"].split())
        if not PLAYER_NAME_MIN <= len(name) <= PLAYER_NAME_MAX:
            raise ApiError(
                "invalid_name",
                f"İsim {PLAYER_NAME_MIN}-{PLAYER_NAME_MAX} karakter olmalı.",
                400,
            )
        if is_inappropriate(name):
            raise ApiError("inappropriate_name", "Bu isim kullanılamaz.", 400)
        entry, rank = services.submit_score(session_id, name)
        data = {
            "entry_id": entry.id,
            "rank": rank,
            "player_name": entry.player_name,
            "score": entry.score,
        }
        return Response(SubmitScoreOutSerializer(data).data, status=status.HTTP_201_CREATED)
