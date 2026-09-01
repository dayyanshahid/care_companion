from urllib.parse import urlencode

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from utils.messages import messages

TEMPLATE = "emails/chat_link.html"


class MailError(Exception):
    """Raised when the mail could not be handed to the mail server."""


def chat_link(conv_id):
    """The chat UI's URL for one conversation."""
    return f"{settings.FRONTEND_URL}?{urlencode({'conv': conv_id})}"


def send_chat_link(to, patient_name, practice, provider, conv_id):
    """Email one patient the link to their chat. Returns the link sent.

    The mail goes out as HTML with a plain-text alternative, so a client that
    will not render the template still gets a readable link.
    """
    if not to:
        raise MailError(messages["noPatientEmail"])

    link = chat_link(conv_id)

    context = {
        "patient_name": patient_name or "there",
        "practice": practice or "your care team",
        "provider": provider or "your care team",
        "link": link,
        "site_url": settings.SITE_URL,
        "privacy_url": settings.PRIVACY_URL,
        "terms_url": settings.TERMS_URL,
        # The portal capture carries no credentials, and the template hides
        # both rows rather than print the mock-up's nephrologist at everyone.
        "provider_title": "",
        "specialties": [],
    }

    text = messages["chatLinkBody"].format(
        name=context["patient_name"],
        practice=context["practice"],
        link=link,
    )

    try:
        mail = EmailMultiAlternatives(
            subject=messages["chatLinkSubject"],
            body=text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to],
        )
        mail.attach_alternative(render_to_string(TEMPLATE, context), "text/html")
        mail.send(fail_silently=False)
    except Exception as exc:
        raise MailError(messages["chatLinkFailed"].format(exc=exc)) from exc

    return link
