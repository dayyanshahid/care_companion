import base64
import time
from email.utils import parseaddr

import httpx
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

from utils.messages import messages

LOGIN_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
SEND_URL = "https://graph.microsoft.com/v1.0/users/{sender}/sendMail"
SCOPE = "https://graph.microsoft.com/.default"

EXPIRY_MARGIN = 60

class GraphMailError(Exception):
    """Raised when Graph would not take the message."""


def _recipients(addresses):
    """Graph's recipient shape for a list of addresses."""
    return [{"emailAddress": {"address": a}} for a in addresses if a]


def _attachments(message):
    """Graph fileAttachment entries for a message's attachments."""
    out = []
    for attachment in message.attachments:
        # Django hands over either a MIMEBase part or a (name, content, type).
        if hasattr(attachment, "get_filename"):
            name = attachment.get_filename() or "attachment"
            content = attachment.get_payload(decode=True) or b""
            mimetype = attachment.get_content_type()
        else:
            name, content, mimetype = attachment
            if isinstance(content, str):
                content = content.encode("utf-8")
        out.append(
            {
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": name,
                "contentType": mimetype or "application/octet-stream",
                "contentBytes": base64.b64encode(content).decode("ascii"),
            }
        )
    return out


def _body(message):
    """The message body, preferring the HTML alternative when there is one."""
    for content, mimetype in getattr(message, "alternatives", []) or []:
        if mimetype == "text/html":
            return {"contentType": "HTML", "content": content}

    content_type = "HTML" if getattr(message, "content_subtype", "plain") == "html" else "Text"
    return {"contentType": content_type, "content": message.body or ""}


class GraphEmailBackend(BaseEmailBackend):
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently)
        self.tenant_id = kwargs.get("tenant_id") or settings.MS_GRAPH_TENANT_ID
        self.client_id = kwargs.get("client_id") or settings.MS_GRAPH_CLIENT_ID
        self.client_secret = kwargs.get("client_secret") or settings.MS_GRAPH_CLIENT_SECRET
        self.sender = kwargs.get("sender") or settings.MS_GRAPH_SENDER_EMAIL
        self.timeout = kwargs.get("timeout") or getattr(settings, "MS_GRAPH_TIMEOUT", 15)
        self.save_to_sent_items = getattr(settings, "MS_GRAPH_SAVE_TO_SENT_ITEMS", False)
        self._token = None
        self._token_expires_at = 0.0

    # --- Token ------------------------------------------------------------
    def _access_token(self):
        if self._token and time.monotonic() < self._token_expires_at:
            return self._token

        if not (self.tenant_id and self.client_id and self.client_secret and self.sender):
            raise GraphMailError(messages["graphNotConfigured"])

        try:
            response = httpx.post(
                LOGIN_URL.format(tenant=self.tenant_id),
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": SCOPE,
                    "grant_type": "client_credentials",
                },
                timeout=self.timeout,
            )
        except httpx.HTTPError as exc:
            raise GraphMailError(messages["graphUnreachable"].format(exc=exc)) from exc

        if response.status_code != 200:
            raise GraphMailError(messages["graphTokenFailed"].format(detail=response.text))

        payload = response.json()
        self._token = payload["access_token"]
        self._token_expires_at = (
            time.monotonic() + max(int(payload.get("expires_in", 3600)) - EXPIRY_MARGIN, 0)
        )
        return self._token

    # --- Sending ----------------------------------------------------------
    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        sent = 0
        for message in email_messages:
            try:
                if self._send(message):
                    sent += 1
            except GraphMailError:
                if not self.fail_silently:
                    raise
        return sent

    def _send(self, message):
        to = list(message.to or [])
        cc = list(message.cc or [])
        bcc = list(message.bcc or [])
        if not (to or cc or bcc):
            return False

        display_name, _address = parseaddr(message.from_email or "")

        payload = {
            "message": {
                "subject": message.subject or "",
                "body": _body(message),
                "toRecipients": _recipients(to),
                "ccRecipients": _recipients(cc),
                "bccRecipients": _recipients(bcc),
                "from": {
                    "emailAddress": (
                        {"address": self.sender, "name": display_name}
                        if display_name
                        else {"address": self.sender}
                    )
                },
            },
            "saveToSentItems": self.save_to_sent_items,
        }

        reply_to = list(message.reply_to or [])
        if reply_to:
            payload["message"]["replyTo"] = _recipients(reply_to)

        attachments = _attachments(message)
        if attachments:
            payload["message"]["attachments"] = attachments

        token = self._access_token()
        try:
            response = httpx.post(
                SEND_URL.format(sender=self.sender),
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
                timeout=self.timeout,
            )
        except httpx.HTTPError as exc:
            raise GraphMailError(messages["graphUnreachable"].format(exc=exc)) from exc

        if response.status_code not in (200, 202):
            raise GraphMailError(messages["graphSendFailed"].format(detail=response.text))

        return True
