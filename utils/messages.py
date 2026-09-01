messages = {
    # --- Generic ------------------------------------------------------------
    "validationFailed": "Validation failed.",
    "internalServerError": "Internal server error.",
    "routeNotFound": "That endpoint does not exist.",

    # --- Chat ---------------------------------------------------------------
    "assistantUnavailable": "The assistant is unavailable right now. Please try again.",
    "portalUnavailable": "The patient portal is unavailable right now. Please try again.",
    "chatNotFound": "Chat not found.",
    "patientNotFound": "No remote patient with that id.",
    "invalidPatientId": "Not a valid patient id.",

    "chatStarted": "Chat started.",
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
        "Emma from {practice} has started a chat with you about the Care "
        "Companion program - a dedicated care manager to support you "
        "between visits.\n\n"
        "Open it here:\n{link}\n\n"
        "The link is yours alone, and opens the same conversation each "
        "time you use it.\n\n"
        "- {practice}"
    ),
    "noPatientEmail": "The patient has no email address on file.",
    "chatLinkFailed": "The chat link could not be emailed: {exc}",

    # --- Knowledge ----------------------------------------------------------
    "searchCompleted": "Search completed successfully.",
    "noSearchResults": "No matching FAQ entries found.",
    "searchUnavailable": "Search is unavailable right now. Please try again.",
    "noFaqEntries": "No FAQ entries found in {path}.",
    "qdrantIngestFailed": "Qdrant rejected the ingest: {exc}",
    "qdrantSearchFailed": "Qdrant could not be searched: {exc}",
    "qdrantReadFailed": "Qdrant could not be read: {exc}",
    "qdrantUnreachable": "Qdrant could not be reached: {exc}",

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
    "qdrantUrlMissing": "QDRANT_URL is not configured.",
    "portalUriMissing": "PORTAL_MONGODB_URI is not configured.",

    # --- Ingest command -----------------------------------------------------
    "ingestCommandHelp": "Parse the FAQ .docx, embed each Q&A with OpenAI, and store it in Qdrant.",
    "ingestPathHelp": "Path to the FAQ .docx file",
    "ingestSuccess": "Ingested {count} FAQ entries.",
}
