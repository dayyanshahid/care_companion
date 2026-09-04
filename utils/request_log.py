import json
import logging
import time

logger = logging.getLogger("api")

PREFIX = "/api/"

BODY_LIMIT = 8000

class RequestLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith(PREFIX):
            return self.get_response(request)

        sent = body(request)
        started = time.monotonic()

        response = self.get_response(request)

        logger.info(
            "%s %s -> %s in %.0fms\n    request : %s\n    response: %s",
            request.method,
            path(request),
            response.status_code,
            (time.monotonic() - started) * 1000,
            sent,
            body(response),
        )

        return response


def path(request):
    query = request.META.get("QUERY_STRING")

    return f"{request.path}?{query}" if query else request.path


def body(message):
    """The payload as one line, compact where it is JSON."""
    try:
        raw = (message.body if hasattr(message, "body") else message.content) or b""
        text = raw.decode("utf-8", "replace")
    except Exception:  
        return "<unavailable>"

    if not text:
        return "<empty>"

    try:
        text = json.dumps(json.loads(text), ensure_ascii=False, separators=(",", ":"))
    except ValueError: 
        text = " ".join(text.split())

    return text if len(text) <= BODY_LIMIT else f"{text[:BODY_LIMIT]}... <truncated>"