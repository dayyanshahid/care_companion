import json

import openai
from django.conf import settings

from api.controllers.chatbot import dal
from api.controllers.prompt import services as prompt_service
from database.serializers import ChatMessageResponseSerializer
from utils import system_prompt
from utils.common import build_error
from utils.enums import HttpStatus, MessageRole
from utils.messages import messages, AssistantError

HISTORY_LIMIT = 40

QUERY_TURNS = 3

SKIP_FIELDS = {"tenant_id", "conv_id", "text"}

CONSENT_LABEL = "CONSENT"

CONSENT_PARTS = ("CONSENT 1", "CONSENT 2", "CONSENT 3")

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
    conv_id, text = body["conv_id"], body["text"]
    values = read_body(body)

    try:
        history = conversation(conv_id, text)
        prompt = build_prompt(tenant_id, values, search_query(history))
        answers = resolve_label(ask_openai(prompt, history), prompt)
    except AssistantError as error:
        raise build_error(
            messages["assistantUnavailable"], HttpStatus.badGateway, error
        ) from error

    if not answers:
        raise build_error(
            messages["emptyAssistantReply"], HttpStatus.badGateway
        )

    return record_turn(conv_id, text, answers)

def record_turn(conv_id, text, answers):
    """Every message is stored; the caller is handed the first of them."""
    try:
        dal.create_message(conv_id, MessageRole.user, text)

        for answer in answers:
            dal.create_message(conv_id, MessageRole.assistant, answer)
    except Exception as error:
        raise build_error(
            messages["turnNotStored"], HttpStatus.badGateway, error
        ) from error

    return ChatMessageResponseSerializer(
        {"conv_id": conv_id, "response": answers[0]}
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
    label = answer.strip().strip("*#.:").strip().upper()
    wording = system_prompt.templates(prompt)

    if label == CONSENT_LABEL:
        parts = [wording[name] for name in CONSENT_PARTS if name in wording]

        if parts:
            return parts

    return [part for part in [wording.get(label) or answer] if part]

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