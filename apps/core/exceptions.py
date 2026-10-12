from rest_framework import exceptions, status
from rest_framework.views import exception_handler


class ApiError(exceptions.APIException):
    """Hata gövdesi: {"error": {"code": ..., "message": ...}}"""

    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, code, message, status_code=None):
        self.code = code
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        super().__init__(detail=message, code=code)


def error_body(code, message, details=None):
    body = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return body


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    details = None
    if isinstance(exc, ApiError):
        code, message = exc.code, exc.message
    elif isinstance(exc, exceptions.ValidationError):
        code, message, details = "validation_error", "Geçersiz istek.", response.data
    elif isinstance(exc, exceptions.Throttled):
        code, message = "throttled", "Çok fazla istek gönderdiniz. Lütfen biraz bekleyin."
    elif isinstance(exc, exceptions.NotFound):
        code, message = "not_found", "Kayıt bulunamadı."
    elif isinstance(exc, exceptions.ParseError):
        code, message = "parse_error", "İstek gövdesi okunamadı."
    elif isinstance(exc, exceptions.MethodNotAllowed):
        code, message = "method_not_allowed", "Bu metot desteklenmiyor."
    elif isinstance(exc, exceptions.UnsupportedMediaType):
        code, message = "unsupported_media_type", "Yalnızca application/json desteklenir."
    else:
        code, message = getattr(exc, "default_code", "error"), str(exc.detail)

    response.data = error_body(code, message, details)
    return response
