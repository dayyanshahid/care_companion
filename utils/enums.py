from enum import IntEnum, StrEnum


def choices(enum):
    return [(member.value, member.name) for member in enum]


class ChatStatus(StrEnum):
    active = "active"
    enrolled = "enrolled"
    declined = "declined"


TAGGED_STATUSES = (
    ChatStatus.enrolled,
    ChatStatus.declined,
)


class Recency(StrEnum):
    oneMonth = "onemonth"
    year = "year"


class MessageRole(StrEnum):
    user = "user"
    assistant = "assistant"


class CaptureType(StrEnum):
    remote = "remote"
    onsite = "onsite"


class ActionType(IntEnum):
    Created = 1
    Updated = 2
    Deleted = 3


class HttpStatus(IntEnum):
    ok = 200
    created = 201
    badRequest = 400
    notFound = 404
    internalServerError = 500
    badGateway = 502


class ErrorCode(IntEnum):
    success = 200
    badRequest = 400
    notFound = 404
    internalServerError = 500
