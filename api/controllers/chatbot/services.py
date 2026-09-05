import re
from uuid import uuid4
import openai
from django.conf import settings
from api.controllers.chatbot import dal
from api.controllers.knowledge import services as knowledge
from database.serializers import ChatMessageResponseSerializer, ChatSerializer
from utils import mailer, prompts, scripts
from utils.common import build_error
from utils.enums import ( ChatStatus, HttpStatus, MessageRole, Recency)
from utils.messages import messages, AssistantError

SCRIPTED = {
    "CONSENT": (scripts.CONSENT, None),
    "ENROLLED": (scripts.WELCOME, ChatStatus.enrolled),
    "DECLINED": (scripts.DECLINE, ChatStatus.declined),
    "CALLBACK": (scripts.CALLBACK, ChatStatus.callback),
    "OPTOUT": (scripts.OPT_OUT, ChatStatus.optedOut),
    "EMERGENCY": (scripts.EMERGENCY, None),
    "CRISIS": (scripts.CRISIS, None),
}

TAG_PATTERN = re.compile(r"<<(%s)>>" % "|".join(SCRIPTED))

ANY_TAG_PATTERN = re.compile(r"<<[A-Z_]+>>")

OPT_OUT_WORDS = {"stop", "stopall", "unsubscribe", "cancel", "quit", "end"}

HISTORY_LIMIT = 40

PROFILE_FIELDS = (
    ("Date of birth", "dob"),
    ("Gender", "gender"),
    ("Patient ID", "ehr_id"),
    ("Mobile", "mobile_phone"),
    ("Email", "email"),
    ("Practice", "practice"),
    ("Provider", "provider"),
    ("Care manager", "care_manager"),
    ("Last appointment", "appointment_date"),
    ("Time since last visit", "data_age"),
)

CHAT_FIELDS = (
    "patient_name",
    "patient_profile",
    "recency",
    "provider",
    "practice",
    "practice_phone",
)

client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)


def send_message(conv_id, text, patient):
    if not conv_id:
        raise build_error(
            messages["conversationIdRequired"], HttpStatus.badRequest
        )

    if not text or not text.strip():
        raise build_error(messages["messageTextRequired"], HttpStatus.badRequest)

    config = build_config(patient or {})

    if is_opt_out(text):
        return record_turn(conv_id, text, scripts.fill(scripts.OPT_OUT, config))

    try:
        context = retrieve_context(text, config)
        history = conversation(conv_id, text)
        answer = ask_openai(prompts.system(config, context), history)
    except AssistantError as error:
        raise build_error(
            messages["assistantUnavailable"], HttpStatus.badGateway, error
        ) from error

    answer, tag = apply_script(answer, config)

    if not answer:
        raise build_error(
            messages["emptyAssistantReply"], HttpStatus.badGateway
        )

    return record_turn(conv_id, text, answer)


def record_turn(conv_id, text, answer):
    try:
        dal.create_message(conv_id, MessageRole.user, text)
        dal.create_message(conv_id, MessageRole.assistant, answer)
    except Exception as error:
        raise build_error(
            messages["turnNotStored"], HttpStatus.badGateway, error
        ) from error

    return ChatMessageResponseSerializer(
        {"conv_id": conv_id, "response": answer}
    ).data


def is_opt_out(text):
    return "".join(c for c in text.lower() if c.isalpha()) in OPT_OUT_WORDS


def apply_script(answer, config):
    if not answer:
        return "", None

    match = TAG_PATTERN.search(answer)

    if not match:
        return ANY_TAG_PATTERN.sub("", answer).strip(), None

    tag = match.group(1)
    script, _ = SCRIPTED.get(tag, (None, None))

    if not script:
        return ANY_TAG_PATTERN.sub("", answer).strip(), None

    return scripts.fill(script, config), tag


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


def build_config(patient):
    name = patient_name(patient)

    return {
        "patient_name": name,
        "patient_profile": build_profile(patient, name),
        "recency": read_recency(patient.get("data_age")),
        "provider": patient.get("provider") or messages["careTeamFallback"],
        "practice": patient.get("practice") or messages["careTeamFallback"],
        "practice_phone": patient.get("practice_phone", ""),
        "care_companion_phone": settings.CARE_COMPANION_PHONE,
    }


def patient_name(patient):
    if not patient:
        return ""

    full = (patient.get("full_name") or "").strip()

    if full:
        return full

    parts = (patient.get("first_name"), patient.get("last_name"))

    return " ".join(part for part in parts if part).strip()


def build_profile(patient, name):
    if not patient:
        return ""

    lines = [f"Name: {name}"] if name else []

    lines += [
        f"{label}: {patient[field]}"
        for label, field in PROFILE_FIELDS
        if patient.get(field)
    ]

    lines += [
        f"{label}: {value}"
        for label, value in (
            ("Conditions", read_conditions(patient.get("codes"))),
            ("Programs", ", ".join(patient.get("programs") or [])),
            ("Caregivers", read_caregivers(patient.get("caregivers"))),
        )
        if value
    ]

    return "\n".join(lines)


def read_conditions(codes):
    """Each coded condition, with the status that says if it is confirmed."""
    named = []

    for code in codes or []:
        label = code.get("description") or code.get("code")

        if not label:
            continue

        status = code.get("status")

        named.append(f"{label} ({status})" if status else label)

    return "; ".join(named)


def read_caregivers(caregivers):
    """Who else is on the record, and how they are related."""
    named = []

    for caregiver in caregivers or []:
        name = caregiver.get("name")

        if not name:
            continue

        relationship = caregiver.get("relationship")

        named.append(f"{name} ({relationship})" if relationship else name)

    return "; ".join(named)


def read_recency(data_age):
    months = "".join(c for c in (data_age or "") if c.isdigit())

    return Recency.oneMonth if months == "1" else Recency.year


def retrieve_context(query, config):
    try:
        results = knowledge.retrieve(query, top_k=settings.RAG_TOP_K)
    except knowledge.KnowledgeError as error:
        raise AssistantError(str(error)) from error

    return "\n\n".join(
        f"Q: {scripts.fill(chunk.question, config)}\n"
        f"A: {scripts.fill(chunk.answer, config)}"
        for chunk, _ in results
        if not scripts.supersedes(chunk.question)
    )


def ask_openai(prompt, history):
    try:
        response = client.responses.create(
            model=settings.OPENAI_MODEL,
            instructions=prompt,
            input=history,
            max_output_tokens=settings.OPENAI_MAX_TOKENS,
        )
    except Exception as error:
        raise AssistantError(str(error)) from error

    return (response.output_text or "").strip()


def start_chat(tenant, patient_id):
    if not patient_id:
        raise build_error(messages["invalidPatientId"], HttpStatus.badRequest)

    if not dal.is_object_id(patient_id):
        raise build_error(messages["invalidPatientId"], HttpStatus.badRequest)

    try:
        capture = dal.get_capture(tenant, patient_id)
    except dal.PortalError as error:
        raise build_error(
            messages["portalUnavailable"], HttpStatus.badGateway, error
        ) from error

    if not capture:
        return None

    chat, is_new_record = dal.upsert_chat(tenant, capture)

    try:
        conv_id, _ = open_conversation(chat)
    except Exception as error:
        if is_new_record:
            dal.delete_chat(chat)

        raise build_error(
            messages["assistantUnavailable"], HttpStatus.badGateway, error
        ) from error

    email_sent, email_error = deliver_chat_link(tenant, capture, chat, conv_id)

    return {
        "conv_id": conv_id,
        "conv_ids": chat.conv_ids,
        "patient_id": str(chat.patient_id) if chat.patient_id else None,
        "patient_name": chat.patient_name,
        "status": chat.status,
        "chat_link": mailer.chat_link(conv_id, tenant),
        "email": capture.get("email", ""),
        "email_sent": email_sent,
        "email_error": email_error,
        "messages": transcript(conv_id),
    }


def open_conversation(chat):
    conv_id = dal.add_conversation(chat, new_conversation_id())

    opener = scripts.fill(scripts.OPENING, chat_config(chat))

    dal.create_message(conv_id, MessageRole.assistant, opener)

    return conv_id, opener


def chat_config(chat):
    config = {field: getattr(chat, field) for field in CHAT_FIELDS}
    config["care_companion_phone"] = settings.CARE_COMPANION_PHONE

    return config


def new_conversation_id():
    return f"conv_{uuid4().hex}"


def deliver_chat_link(tenant, capture, chat, conv_id):
    if not capture.get("email"):
        return False, messages["noPatientEmail"]

    try:
        mailer.send_chat_link(
            capture.get("email"),
            chat.patient_name,
            chat.practice,
            chat.provider,
            conv_id,
            tenant,
        )
    except mailer.MailError as error:
        return False, str(error)

    return True, ""

def read_conversation(ident):
    if dal.is_object_id(ident):
        return messages["conversationsRetrieved"], list_conversations(ident)

    return messages["transcriptRetrieved"], transcript(ident)


def list_conversations(patient_id=None):
    if patient_id and not dal.is_object_id(patient_id):
        raise build_error(messages["invalidPatientId"], HttpStatus.badRequest)

    try:
        chats = dal.find_started_chats(patient_id)

        return ChatSerializer(chats, many=True).data
    except Exception as error:
        raise build_error(
            messages["chatsUnavailable"], HttpStatus.badGateway, error
        ) from error


def transcript(conv_id):
    if not conv_id:
        return []

    try:
        return [
            {
                "role": message.role,
                "text": message.text,
                "created_at": message.created_at,
            }
            for message in dal.find_messages(conv_id)
        ]
    except Exception as error:
        raise build_error(
            messages["transcriptUnavailable"], HttpStatus.badGateway, error
        ) from error


def list_patients(tenant):
    try:
        return dal.list_captures(tenant)
    except dal.PortalError as error:
        raise build_error(
            messages["portalUnavailable"], HttpStatus.badGateway, error
        ) from error
