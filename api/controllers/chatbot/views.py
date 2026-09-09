import json

from django.http import StreamingHttpResponse
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from api.controllers.chatbot import services
from database.serializers import ChatMessagePayloadSerializer
from utils.common import ApiError, ResponseHelper
from utils.enums import HttpStatus
from utils.messages import messages


def stream(_common, results):
    for result in results:
        yield json.dumps(
            _common.success(messages["messageSent"], HttpStatus.ok, result)
        ) + "\n"


@api_view(["POST"])
def send_message(request):
    _common = ResponseHelper()

    try:
        payload = ChatMessagePayloadSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        results = services.send_message(payload.validated_data)

        return StreamingHttpResponse(
            stream(_common, results),
            content_type="application/x-ndjson",
        )
    except ValidationError:
        raise
    except ApiError as error:
        return Response(
            _common.error(error.message, error.code, error.error),
            status=error.code,
        )
    except Exception as error:
        return Response(
            _common.error(
                messages["internalServerError"],
                HttpStatus.internalServerError,
                error,
            ),
            status=HttpStatus.internalServerError,
        )