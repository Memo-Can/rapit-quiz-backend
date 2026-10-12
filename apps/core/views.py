from django.http import JsonResponse

from .exceptions import error_body


def not_found(request, exception=None):
    return JsonResponse(error_body("not_found", "Kayıt bulunamadı."), status=404)


def server_error(request):
    return JsonResponse(error_body("server_error", "Beklenmeyen bir hata oluştu."), status=500)
