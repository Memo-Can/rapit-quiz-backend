import logging

from django.db import connection
from django.http import JsonResponse

logger = logging.getLogger(__name__)

HEALTH_PATH = "/api/v1/health/"


class HealthCheckMiddleware:
    """Sağlık kontrolünü en başta yanıtlar.

    App Platform health check isteklerinin Host başlığı ALLOWED_HOSTS ile eşleşmeyebilir
    ve HTTPS yönlendirmesine takılmamalıdır; bu yüzden host doğrulamasından önce çalışır.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == HEALTH_PATH and request.method in ("GET", "HEAD"):
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
            except Exception:
                logger.exception("Health check: veritabanına bağlanılamadı")
                return JsonResponse({"status": "error", "database": "down"}, status=503)
            return JsonResponse({"status": "ok", "database": "up"})
        return self.get_response(request)
