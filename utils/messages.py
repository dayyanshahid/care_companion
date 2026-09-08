from utils.enums import HttpStatus

messages = {
    # --- Generic ------------------------------------------------------------
    "validationFailed": "Validation failed.",
    "internalServerError": "Internal server error.",
    "routeNotFound": "That endpoint does not exist.",
    "careTeamFallback": "your care team",

    # --- Chat ---------------------------------------------------------------
    "assistantUnavailable": "The assistant is unavailable right now. Please try again.",
    "messageSent": "Message sent.",
    "emptyAssistantReply": (
        "The assistant returned nothing. Please try again."
    ),
    "transcriptUnavailable": (
        "The conversation could not be read right now. Please try again."
    ),
    "turnNotStored": (
        "The reply was produced but could not be saved. Please try again."
    ),

    # --- System prompt ------------------------------------------------------
    "promptFetched": "System prompt loaded.",
    "promptNotConfigured": (
        "No system prompt has been configured. Add one through the "
        "prompt API before starting a conversation."
    ),
    "promptUpdated": "System prompt updated.",
    "nothingToUpdate": "Send a system prompt, a chatbot name, or a file.",
    "invalidTenantId": "tenant_id must be a 24-character ObjectId.",
    "fileTypeUnsupported": (
        "{name} is not a supported document. Upload .pdf, .docx, .txt or .md."
    ),
    "fileUnreadable": "That document could not be read.",
    "documentsUnavailable": (
        "The documents could not be prepared right now. Please try again."
    ),
    "storageUnavailable": (
        "The document store is unavailable right now. Please try again."
    ),

    # --- Configuration ------------------------------------------------------
    "openaiKeyMissing": "OPENAI_API_KEY is not configured.",
    "s3BucketMissing": "S3_BUCKET is not configured.",
}

class AppError(Exception):
    key = "internalServerError"

    def __init__(self, detail=None):
        self.detail = detail or messages[self.key]

        super().__init__(self.detail)


class ApiError(AppError):
    def __init__(self, message=None, code=HttpStatus.badRequest, error=None):
        super().__init__(message)

        self.message = self.detail
        self.code = code
        self.error = error


class AssistantError(AppError):
    key = "assistantUnavailable"


class StorageError(AppError):
    key = "storageUnavailable"


class DocumentError(AppError):
    key = "fileUnreadable"


class EmbeddingError(AppError):
    key = "documentsUnavailable"
