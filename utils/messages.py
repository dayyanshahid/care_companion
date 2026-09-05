from utils.enums import HttpStatus

messages = {
    # --- Generic ------------------------------------------------------------
    "validationFailed": "Validation failed.",
    "internalServerError": "Internal server error.",
    "routeNotFound": "That endpoint does not exist.",
    "careTeamFallback": "your care team",

    # --- Log lines ----------------------------------------------------------
    # --- Chat ---------------------------------------------------------------
    "assistantUnavailable": "The assistant is unavailable right now. Please try again.",
    "portalUnavailable": "The patient portal is unavailable right now. Please try again.",
    "chatNotFound": "Chat not found.",
    "conversationIdRequired": "A conversation id is required.",
    "messageTextRequired": "A message is required.",
    "emptyAssistantReply": (
        "The assistant returned nothing. Please try again."
    ),
    "transcriptUnavailable": (
        "The conversation could not be read right now. Please try again."
    ),
    "chatsUnavailable": (
        "Chats could not be read right now. Please try again."
    ),
    "turnNotStored": (
        "The reply was produced but could not be saved. Please try again."
    ),
    "patientNotFound": "No remote patient with that id.",
    "invalidPatientId": "Not a valid patient id.",

    # --- Tenant -------------------------------------------------------------
    "tenantHeaderMissing": "The X-Tenant header is required.",
    "tenantUnknown": "No tenant is served at '{subdomain}'.",
    "tenantRegistryUnavailable": (
        "The tenant registry is unavailable right now. Please try again."
    ),

    "chatStarted": "Chat started.",
    "chatStartedNoEmail": (
        "Chat started, but the link could not be emailed to the patient. "
        "Share the chat link with them instead."
    ),
    "messageSent": "Message sent.",
    "conversationsRetrieved": "Conversations retrieved successfully.",
    "noConversations": "No conversations found.",
    "noPatients": "No remote patients found.",
    "nothingFound": "Nothing found for that id.",
    "transcriptRetrieved": "Transcript retrieved successfully.",
    "patientsRetrieved": "Patients retrieved successfully.",

    # --- Chat link email ----------------------------------------------------
    "chatLinkSubject": "Your Care Companion chat is ready",
    "chatLinkBody": (
        "Hi {name},\n\n"
        "The Care Companion assistant from {practice} has started a chat "
        "with you about the Care "
        "Companion program - a dedicated care manager to support you "
        "between visits.\n\n"
        "Open it here:\n{link}\n\n"
        "The link is yours alone, and opens the same conversation each "
        "time you use it.\n\n"
        "- {practice}"
    ),
    "noPatientEmail": "The patient has no email address on file.",
    "mailFailed": "The email could not be sent.",
    "graphFailed": "Microsoft Graph would not take the message.",
    "invalidPatientEmail": "The patient's email address is not valid: {email}",
    "chatLinkFailed": "The chat link could not be emailed: {exc}",

    # --- Knowledge ----------------------------------------------------------
    "searchCompleted": "Search completed successfully.",
    "noSearchResults": "No matching FAQ entries found.",
    "searchUnavailable": "Search is unavailable right now. Please try again.",
    "noFaqEntries": "No FAQ entries found in {path}.",
    "noFaqStored": (
        "The FAQ has not been ingested yet. Run: "
        "manage.py ingest_faq <path to the FAQ .docx>"
    ),

    # --- Configuration ------------------------------------------------------
    "openaiKeyMissing": "OPENAI_API_KEY is not configured.",
    "graphNotConfigured": (
        "Microsoft Graph mail is not configured: MS_GRAPH_TENANT_ID, "
        "MS_GRAPH_CLIENT_ID, MS_GRAPH_CLIENT_SECRET and MS_GRAPH_SENDER_EMAIL "
        "are all required."
    ),
    "graphTokenFailed": "Microsoft Graph refused the sign-in: {detail}",
    "graphSendFailed": "Microsoft Graph refused the message: {detail}",
    "graphUnreachable": "Microsoft Graph could not be reached: {exc}",
    "centralUriMissing": "CENTRAL_MONGODB_URI is not configured.",

    # --- Ingest command -----------------------------------------------------
    "ingestCommandHelp": "Parse the FAQ .docx, embed each Q&A with OpenAI, and store it in MongoDB.",
    "ingestPathHelp": "Path to the FAQ .docx file",
    "ingestSuccess": "Ingested {count} FAQ entries.",
}

# --- Errors -------------------------------------------------------------
# Raised by the application. Each one names the message above that it
# carries when no detail is given.


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


class KnowledgeError(AppError):
    key = "searchUnavailable"


class PortalError(AppError):
    key = "portalUnavailable"


class TenantError(AppError):
    key = "tenantRegistryUnavailable"


class MailError(AppError):
    key = "mailFailed"


class GraphMailError(MailError):
    key = "graphFailed"
