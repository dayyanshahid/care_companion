import json

import openai
from django.conf import settings

from api.controllers.chatbot import dal
from api.controllers.prompt import services as prompt_service
from database.serializers import ChatMessageResponseSerializer
from utils import system_prompt
from utils.common import build_error
from utils.enums import ActionType, HttpStatus, MessageRole
from utils.messages import messages, AssistantError

HISTORY_LIMIT = 40

QUERY_TURNS = 3

SKIP_FIELDS = {"tenant_id", "conv_id", "text"}

_openai_client = None

def read_body(body):
    lines = [] 

    for field, value in body.items():
        if field in SKIP_FIELDS or not value:
            continue

        if isinstance(value, (list, dict)):
            value = json.dumps(value, default=str)

        lines.append(f"{field}: {value}")

    return {
        "record": "\n".join(lines),
        "patient_name": body["fullName"].strip() or f"{body['firstName']} {body['lastName']}".strip(),
        "provider": body["providerName"] or messages["careTeamFallback"],
        "practice": body["practiceName"] or messages["careTeamFallback"],
        "practice_phone": body["practice_phone"],
        "care_companion_phone": next(
            (c["phone"].strip() for c in body["caregivers"] if c["phone"].strip()), ""
        ),
    }

def send_message(body):
    tenant_id = body["tenant_id"]
    conv_id, text = body["conv_id"], body["text"].strip()

    queued = dal.next_queued(conv_id)

    if queued:
        return deliver(conv_id, text, queued)

    if not text:
        raise build_error(messages["nothingQueued"])

    values = read_body(body)

    try:
        history = conversation(conv_id, text)
        prompt = build_prompt(tenant_id, values, search_query(history))
        answer = resolve_label(ask_openai(prompt, history), prompt)
    except AssistantError as error:
        raise build_error(
            messages["assistantUnavailable"], HttpStatus.badGateway, error
        ) from error

    if not answer:
        raise build_error(
            messages["emptyAssistantReply"], HttpStatus.badGateway
        )

    return record_turn(conv_id, text, answer)

def record_turn(conv_id, text, answer):
    """Send the first text back and leave the rest for the calls that follow.

    A reply carries one message, so the second and third consent texts are
    written as queued and wait here until the caller comes back for them.
    """
    first, later = answer[0], answer[1:]

    try:
        dal.create_message(conv_id, MessageRole.user, text)
        dal.create_message(conv_id, MessageRole.assistant, first)

        for part in later:
            dal.create_message(
                conv_id, MessageRole.assistant, part, ActionType.Queued
            )
    except Exception as error:
        raise build_error(
            messages["turnNotStored"], HttpStatus.badGateway, error
        ) from error

    return reply(conv_id, first)


def deliver(conv_id, text, queued):
    """Hand over the next queued text instead of asking the model again.

    The follow-on call is made automatically and carries no patient message,
    so there is nothing to answer - only the message already written.
    """
    try:
        if text:
            dal.create_message(conv_id, MessageRole.user, text)

        dal.mark_sent(queued)
    except Exception as error:
        raise build_error(
            messages["turnNotStored"], HttpStatus.badGateway, error
        ) from error

    return reply(conv_id, queued.text)


def reply(conv_id, answer):
    return ChatMessageResponseSerializer(
        {"conv_id": conv_id, "response": answer}
    ).data

def conversation(conv_id, text):
    try:
        earlier = [
            {"role": message.role, "content": message.text}
            for message in dal.find_messages(conv_id)
        ]
    except Exception as error:
        raise build_error(
            messages["transcriptUnavailable"], HttpStatus.badGateway, error
        ) from error

    return [
        *earlier,
        {"role": MessageRole.user, "content": text},
    ][-HISTORY_LIMIT:]

def search_query(history):
    return "\n".join(turn["content"] for turn in history[-QUERY_TURNS:])


def build_prompt(tenant_id, values, query=""):
    stored = prompt_service.current(tenant_id, query)
    parts = [f"PATIENT RECORD:\n{values['record']}"]

    if stored["name"]:
        parts.append(
            f"CHATBOT NAME:\n{stored['name']} - this is what you are called. "
            "Give this name when a patient asks who they are speaking to."
        )

    parts.append(stored["body"])

    if stored["knowledge"]:
        parts.append(f"APPROVED DOCUMENTS:\n{stored['knowledge']}")

    return system_prompt.fill("\n\n".join(parts), values)

def resolve_label(answer, prompt):
    """Turn the model's reply into the texts the patient receives.

    A bare label stands for reviewed wording, and that wording may itself be
    written as several texts - the consent points go out as three - so every
    reply leaves here as a list, of one part or of many.
    """
    label = answer.strip().strip("*#.:").strip().upper()

    return system_prompt.parts(
        system_prompt.templates(prompt).get(label) or answer
    )

def client():
    global _openai_client

    if _openai_client is None:
        if not settings.OPENAI_API_KEY:
            raise AssistantError(messages["openaiKeyMissing"])

        _openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

    return _openai_client

def ask_openai(prompt, history):
    api = client()

    try:
        response = api.responses.create(
            model=settings.OPENAI_MODEL,
            instructions=prompt,
            input=history,
            max_output_tokens=settings.OPENAI_MAX_TOKENS,
        )
    except Exception as error:
        raise AssistantError(str(error)) from error

    return (response.output_text or "").strip()