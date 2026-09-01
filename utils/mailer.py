from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.core.validators import validate_email
from django.template.loader import render_to_string

from utils.messages import messages

TEMPLATE = "emails/chat_link.html"


class MailError(Exception):
    """Raised when the mail could not be handed to the mail server."""


def chat_link(conv_id, tenant):
    # <subdomain>/chat/<conv_id>. The host is the tenant's own, which is also
    # how the page knows which tenant it is for - it is opened from an email,
    # with no portal around it to say.
    base = tenant["subdomain"].rstrip("/")

    return f"{base}{settings.FRONTEND_PATH}/{conv_id}"


def send_chat_link(to, patient_name, practice, provider, conv_id, tenant):
    if not to:
        raise MailError(messages["noPatientEmail"])

    try:
        validate_email(to)
    except ValidationError:
        raise MailError(messages["invalidPatientEmail"].format(email=to))

    link = chat_link(conv_id, tenant)

    context = {
        "patient_name": patient_name or "there",
        "practice": practice or "your care team",
        "provider": provider or "your care team",
        "link": link,
        "assets": settings.ASSETS_URL,
        "site_url": tenant["subdomain"],
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
