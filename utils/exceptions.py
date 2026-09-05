"""Every error this project raises itself.

One home, so a caller can see the whole list, and so no wording is written at
a raise site: each class names a key and the text comes from messages.py.
"""
from utils.enums import HttpStatus
from utils.messages import messages


class AppError(Exception):
    """Base for the project's own errors.

    Raised bare it carries its class's message from messages.py; raised with
    a detail - usually the underlying failure - it carries that instead.
    """

    message_key = "internalServerError"

    def __init__(self, detail=None):
        self.detail = detail or messages[self.message_key]

        super().__init__(self.detail)


class ApiError(AppError):
    """An error meant for the caller: it carries the status to answer with."""

    def __init__(self, message=None, code=HttpStatus.badRequest, error=None):
        super().__init__(message)

        self.message = self.detail
        self.code = code
        self.error = error


class AssistantError(AppError):
    """The assistant itself failed - OpenAI, or the FAQ behind it."""

    message_key = "assistantUnavailable"


class KnowledgeError(AppError):
    """The FAQ could not be parsed, embedded or searched."""

    message_key = "searchUnavailable"


class PortalError(AppError):
    """The tenant's patient portal could not be reached or read."""

    message_key = "portalUnavailable"


class TenantError(AppError):
    """The tenant registry could not be read, or a record is unusable."""

    message_key = "tenantRegistryUnavailable"


class MailError(AppError):
    """The mail could not be handed to the mail server."""

    message_key = "mailFailed"


class GraphMailError(MailError):
    """Microsoft Graph would not take the message."""

    message_key = "graphFailed"
