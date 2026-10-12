from django.conf import settings
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.categories.models import Category
from apps.core.exceptions import ApiError

from .models import ScoreEntry
from .serializers import LeaderboardEntrySerializer


class LeaderboardView(APIView):
    @extend_schema(
        summary="Kategorinin skor tablosu",
        parameters=[
            OpenApiParameter("category", str, required=True, description="Kategori slug'ı"),
            OpenApiParameter("limit", int, description="Varsayılan 10, en fazla 50"),
        ],
        responses={200: LeaderboardEntrySerializer(many=True)},
    )
    def get(self, request):
        slug = request.query_params.get("category")
        if not slug:
            raise ApiError("category_required", "category parametresi zorunludur.", 400)
        try:
            category = Category.objects.get(slug=slug, is_active=True)
        except Category.DoesNotExist:
            raise ApiError("category_not_found", "Kategori bulunamadı.", 404)

        try:
            limit = int(request.query_params.get("limit", settings.LEADERBOARD_DEFAULT_LIMIT))
        except ValueError:
            raise ApiError("invalid_limit", "limit bir tam sayı olmalı.", 400)
        limit = max(1, min(limit, settings.LEADERBOARD_MAX_LIMIT))

        entries = ScoreEntry.objects.filter(category=category)[:limit]
        data = [
            {
                "rank": rank,
                "entry_id": e.id,
                "player_name": e.player_name,
                "score": e.score,
                "correct_count": e.correct_count,
                "total_time_ms": e.total_time_ms,
            }
            for rank, e in enumerate(entries, start=1)
        ]
        return Response(LeaderboardEntrySerializer(data, many=True).data)
