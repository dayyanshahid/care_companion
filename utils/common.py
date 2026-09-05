from django.http import JsonResponse
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from utils.enums import HttpStatus
from utils.messages import messages, ApiError


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
    if isinstance(exc, ApiError):
        return Response(
            error(exc.message, exc.code, exc.error), status=exc.code
        )

    handled = drf_exception_handler(exc, context)

    if handled is None:  
        return None

    if isinstance(exc, ValidationError):
        body = error(messages["validationFailed"], handled.status_code)
        body["result"] = handled.data 
    else:
        detail = handled.data.get("detail", handled.data)
        body = error(str(detail), handled.status_code)

    handled.data = body

    return handled

def not_found(request, exception=None):
    return JsonResponse(
        error(messages["routeNotFound"], HttpStatus.notFound),
        status=HttpStatus.notFound,
    )

def server_error(request):
    return JsonResponse(
        error(messages["internalServerError"], HttpStatus.internalServerError),
        status=HttpStatus.internalServerError,
    )