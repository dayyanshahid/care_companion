from enum import IntEnum, StrEnum


def choices(enum):
    return [(member.value, member.name) for member in enum]


class ChatStatus(StrEnum):
    # The conversation is still going - nothing has been settled yet.
    active = "active"
    enrolled = "enrolled"
    declined = "declined"


# The two outcomes the assistant can tag a reply with. Anything untagged
# leaves the chat `active`, which is what "still talking" means.
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
