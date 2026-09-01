from django.http import JsonResponse
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from utils.enums import HttpStatus
from utils.messages import messages

class ApiError(Exception):
    """An error that knows the status it should be reported with.

    Raised by the service layer, rendered by `exception_handler` below. It is
    what keeps the views free of error handling - a service says what went
    wrong and with which status, and no view has to catch anything.
    """

    def __init__(self, message, code=HttpStatus.badRequest, error=None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.error = error


def build_error(message, code=HttpStatus.badRequest, error=None):
    return ApiError(message, code, error)


class ResponseHelper:
    def success(self, message, response_code=HttpStatus.ok, data=None):
        return {
            "response_code": response_code,
            "success": True,
            "status_code": response_code,
            "message": message,
            "result": data,
        }

    def error(self, message, response_code=HttpStatus.badRequest, error=None):
        return {
            "response_code": response_code,
            "success": False,
            "status_code": response_code,
            "message": message,
            "result": None,
            "error_message": str(error) if error else None,
        }


response = ResponseHelper()
success, error = response.success, response.error


def exception_handler(exc, context):
    """DRF's errors - validation, 405 - and our own, in the shape above."""
    if isinstance(exc, ApiError):
        return Response(
            error(exc.message, exc.code, exc.error), status=exc.code
        )

    handled = drf_exception_handler(exc, context)

    if handled is None:  # not an APIException; server_error takes it
        return None

    if isinstance(exc, ValidationError):
        body = error(messages["validationFailed"], handled.status_code)
        body["result"] = handled.data  # the per-field errors
    else:
        detail = handled.data.get("detail", handled.data)
        body = error(str(detail), handled.status_code)

    handled.data = body

    return handled

def not_found(request, exception=None):
    """404 for a path that matches no route. Django resolves before DRF."""
    return JsonResponse(
        error(messages["routeNotFound"], HttpStatus.notFound),
        status=HttpStatus.notFound,
    )

def server_error(request):
    """500 for anything that escaped a view."""
    return JsonResponse(
        error(messages["internalServerError"], HttpStatus.internalServerError),
        status=HttpStatus.internalServerError,
    )
