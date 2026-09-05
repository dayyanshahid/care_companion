from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from api.controllers.chatbot import services
from database.serializers import (
    ChatMessagePayloadSerializer,
    ChatStartSerializer,
)
from utils import tenant as tenants
from utils.common import ApiError, ResponseHelper
from utils.enums import HttpStatus
from utils.messages import messages


@api_view(["POST"])
def start_chat(request):
    _common = ResponseHelper()

    try:
        payload = ChatStartSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        tenant = tenants.from_request(request)
        patient_id = payload.validated_data["patient_id"]

        result = services.start_chat(tenant, patient_id)

        if result:
            started = (
                messages["chatStarted"]
                if result["email_sent"]
                else messages["chatStartedNoEmail"]
            )

            return Response(
                _common.success(started, HttpStatus.created, result),
                status=HttpStatus.created,
            )
        else:
            return Response(
                _common.error(messages["patientNotFound"], HttpStatus.notFound),
                status=HttpStatus.notFound,
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


@api_view(["POST"])
def send_message(request):
    _common = ResponseHelper()

    try:
        payload = ChatMessagePayloadSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        body = payload.validated_data

        patient = {
            "full_name": body["fullName"],
            "first_name": body["firstName"],
            "last_name": body["lastName"],
            "dob": body["dob"],
            "gender": body["gender"],
            "ehr_id": body["ehrId"],
            "mobile_phone": body["mobilePhone"],
            "email": body["email"],
            "practice": body["practiceName"],
            "practice_phone": body["practice_phone"],
            "provider": body["providerName"],
            "care_manager": body["careManager"],
            "appointment_date": body["appointmentDate"],
            "data_age": body["dataAge"],
            "care_manager_id": body["careManagerId"],
            "caregivers": body["caregivers"],
            "codes": body["codes"],
            "programs": body["programs"],
        }

        result = services.send_message(
            conv_id=body["conv_id"],
            text=body["text"],
            patient=patient,
        )

        if result:
            return Response(
                _common.success(messages["messageSent"], HttpStatus.ok, result)
            )
        else:
            return Response(
                _common.error(messages["chatNotFound"], HttpStatus.notFound),
                status=HttpStatus.notFound,
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


@api_view(["GET"])
def list_conversations(request):
    _common = ResponseHelper()

    try:
        patient_id = request.query_params.get("patient_id")

        result = services.list_conversations(patient_id)

        if result:
            return Response(
                _common.success(
                    messages["conversationsRetrieved"], HttpStatus.ok, result
                )
            )
        else:
            return Response(
                _common.success(
                    messages["noConversations"], HttpStatus.ok, result
                )
            )
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


@api_view(["GET"])
def read_conversation(request, ident):
    _common = ResponseHelper()

    try:
        message, result = services.read_conversation(ident)

        if result:
            return Response(_common.success(message, HttpStatus.ok, result))
        else:
            return Response(
                _common.success(messages["nothingFound"], HttpStatus.ok, result)
            )
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


@api_view(["GET"])
def list_patients(request):
    _common = ResponseHelper()

    try:
        tenant = tenants.from_request(request)

        result = services.list_patients(tenant)

        if result:
            return Response(
                _common.success(
                    messages["patientsRetrieved"], HttpStatus.ok, result
                )
            )
        else:
            return Response(
                _common.success(messages["noPatients"], HttpStatus.ok, result)
            )
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