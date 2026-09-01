import logging
import re

import openai
from django.conf import settings

from api.controllers.chatbot import dal
from api.controllers.knowledge import services as knowledge
from database.serializers import ChatMessageResponseSerializer, ChatSerializer
from utils import mailer
from utils.common import build_error
from utils.enums import (
    HttpStatus,
    MessageRole,
    Recency,
    TAGGED_STATUSES,
)
from utils.messages import messages

logger = logging.getLogger(__name__)


PLACEHOLDERS = {
    "[Provider name]": "provider",
    "[Practice name]": "practice",
    "[Patient Name]": "patient_name",
}

PHONE_FALLBACKS = (
    (", [Care Companion number]", ""),
    ("[Care Companion number]", "the Care Companion number"),
    ("[Practice Phone Number]", "the practice"),
    ("[Practice phone]", "the practice"),
)

STATUS_MAP = {status.value.upper(): status.value for status in TAGGED_STATUSES}

STATUS_PATTERN = re.compile(r"<<(%s)>>" % "|".join(STATUS_MAP))

# Anything tag-shaped, so a stray or retired tag is scrubbed rather than read.
ANY_TAG_PATTERN = re.compile(r"<<[A-Z_]+>>")

# Everything the chat holds about its patient, reused on every turn.
CONFIG_FIELDS = (
    "patient_name",
    "patient_profile",
    "recency",
    "provider",
    "practice",
)

client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)


class ChatServiceError(Exception):
    """A failure inside the assistant itself - OpenAI, or the FAQ behind it."""


def start_chat(patient_id):
    try:
        capture = dal.get_capture(patient_id)
    except dal.PortalError as exc:
        raise build_error(
            messages["portalUnavailable"], HttpStatus.badGateway, exc
        ) from exc

    if not capture:
        return None

    chat, is_new_record = dal.upsert_chat(capture)

    try:
        conv_id, _ = open_conversation(chat)
    except ChatServiceError as exc:
        if is_new_record:
            dal.delete_chat(chat)

        raise build_error(
            messages["assistantUnavailable"], HttpStatus.badGateway, exc
        ) from exc

    return {
        "conv_id": conv_id,
        "conv_ids": chat.conv_ids,
        "patient_id": str(chat.patient_id) if chat.patient_id else None,
        "patient_name": chat.patient_name,
        "status": chat.status,
        "chat_link": mailer.chat_link(conv_id),
        "email": capture.get("email", ""),
        "email_sent": deliver_chat_link(capture, chat, conv_id),
        "messages": transcript(conv_id),
    }


def send_message(conv_id, text):
    chat = dal.find_chat_by_conversation(conv_id)

    if not chat:
        return None

    try:
        answer, status = reply_to(chat, conv_id, text)
    except ChatServiceError as exc:
        raise build_error(
            messages["assistantUnavailable"], HttpStatus.badGateway, exc
        ) from exc

    return ChatMessageResponseSerializer(
        {"conv_id": conv_id, "response": answer, "status": status}
    ).data


def list_conversations(patient_id=None):
    if patient_id and not dal.is_object_id(patient_id):
        raise build_error(messages["invalidPatientId"], HttpStatus.badRequest)

    return ChatSerializer(
        dal.find_started_chats(patient_id), many=True
    ).data


def read_conversation(ident):
    if dal.is_object_id(ident):
        return messages["conversationsRetrieved"], list_conversations(ident)

    return messages["transcriptRetrieved"], transcript(ident)


def list_patients():
    """Every remote patient the portal holds."""
    try:
        return dal.list_captures()
    except dal.PortalError as exc:
        raise build_error(
            messages["portalUnavailable"], HttpStatus.badGateway, exc
        ) from exc


def deliver_chat_link(capture, chat, conv_id):
    try:
        mailer.send_chat_link(
            capture.get("email"),
            chat.patient_name,
            chat.practice,
            chat.provider,
            conv_id,
        )
    except mailer.MailError as exc:
        logger.warning("Chat %s: %s", conv_id, exc)

        return False

    return True


def transcript(conv_id):
    return [
        {
            "role": message.role,
            "text": message.text,
            "created_at": message.created_at,
        }
        for message in dal.find_messages(conv_id)
    ]


# --- The assistant ----------------------------------------------------------

def open_conversation(chat):
    conv_id = dal.add_conversation(chat, create_openai_conversation())

    config = build_config(chat)
    opener = build_opener(config)

    dal.create_message(chat, conv_id, MessageRole.assistant, opener)

    # Seed the OpenAI conversation with the opener so it has the same history.
    ask_openai(
        conv_id=conv_id,
        prompt=build_system_prompt(config, ""),
        text=opener,
    )

    return conv_id, opener


def reply_to(chat, conv_id, text):
    dal.create_message(chat, conv_id, MessageRole.user, text)

    config = build_config(chat)
    context = retrieve_context(text, config)

    answer = ask_openai(
        conv_id=conv_id,
        prompt=build_system_prompt(config, context),
        text=text,
    )

    answer, status = parse_status(answer)

    dal.create_message(chat, conv_id, MessageRole.assistant, answer)

    if status:
        dal.set_chat_status(chat, status)

    return answer, chat.status


def build_config(chat):
    return {field: getattr(chat, field) for field in CONFIG_FIELDS}


def create_openai_conversation():
    try:
        return client.conversations.create().id
    except Exception as exc:
        raise ChatServiceError(str(exc)) from exc


def ask_openai(conv_id, prompt, text):
    try:
        response = client.responses.create(
            model=settings.OPENAI_MODEL,
            conversation=conv_id,
            instructions=prompt,
            input=text,
            max_output_tokens=settings.OPENAI_MAX_TOKENS,
        )
    except Exception as exc:
        raise ChatServiceError(str(exc)) from exc

    return response.output_text


def retrieve_context(query, config):
    try:
        results = knowledge.retrieve(
            query,
            top_k=settings.RAG_TOP_K,
        )
    except knowledge.KnowledgeError as exc:
        raise ChatServiceError(str(exc)) from exc

    return "\n\n".join(
        f"Q: {fill(chunk.question, config)}\n"
        f"A: {fill(chunk.answer, config)}"
        for chunk, _ in results
    )


def fill(text, config):

    for placeholder, field in PLACEHOLDERS.items():
        value = config.get(field) or ""

        if value:
            text = text.replace(placeholder, value)

    for placeholder, replacement in PHONE_FALLBACKS:
        text = text.replace(placeholder, replacement)

    return text


def build_opener(config):
    patient = config["patient_name"]
    provider = config["provider"]
    practice = config["practice"]

    
    office = f"{provider}'s office" if provider else "your care team"
    where = f" at {practice}" if practice else ""
    asked = provider or "your care team"

    opening = f"Hi {patient}! This is Emma from {office}{where}."

    intro = {
        Recency.oneMonth: (
            f"{opening} It's been about a month since your last visit, and "
            f"{asked} wanted us to check in about our Care Companion program."
        ),
        Recency.year: (
            f"{opening} It's been about a year since we last saw you, and "
            f"{asked} wanted us to reach out about our Care Companion program."
        ),
    }.get(config.get("recency"))

    if not intro:
        intro = (
            f"{opening} {asked} asked us to reach out about our Care "
            "Companion program."
        )

    return (
        f"{intro} You'd get a dedicated care manager to support you between "
        "visits — help with your medications, appointments, diet, and keeping "
        "an eye on your vitals. It's covered by Medicare, Medicare Advantage, "
        "and most commercial plans. Would it be alright if I shared a little more?"
    )


def build_system_prompt(config, context):
    provider = config["provider"] or "your care team"
    practice = config["practice"] or "your care team"

    # Emma has no number to give, and must not invent one.
    no_phone = (
        "Never state a phone number. You do not have one, so do not "
        f'invent one - refer to "{config["practice"] or "the practice"}" '
        'or "the office" instead.'
    )

    recency = {
        Recency.oneMonth: "The patient was last seen about one month ago.",
        Recency.year: "The patient was last seen about one year ago.",
    }.get(config.get("recency"), "The patient was last seen about one year ago.")

    context = context or "(No relevant FAQ was found.)"
    profile = config.get("patient_profile") or f"Name: {config['patient_name']}"

    return f"""
You are Emma, a warm, human-sounding enrollment assistant for
{provider}'s office at {practice}.

You help patients enroll in the Care Companion program.

PATIENT RECORD
This is the patient's complete record from the practice.

{profile}

{recency}

Use it to speak to them personally and to answer questions about their own
details - their provider, their care manager, their appointment, their
insurance, the conditions the programme would help them manage. `codes` with
status "chronic" are confirmed; "pending" ones are not yet theirs, so do not
present them as diagnoses.

Never read the record out at them, never list their diagnoses unprompted, and
never state anything about them that is not in the record above. It is their
own information, so you may confirm a detail they ask about - but do not
recite contact details, addresses or identifiers back at them unprompted, and
never repeat their SSN digits.

IMPORTANT:
The opening message has already been sent. Do not repeat it.

SCOPE:
You are here for two things only: the Care Companion program - what it is,
what it covers, what it costs, who provides it, how to join or leave - and
the patient's own record above.

Everything else is out of scope: small talk, news, weather, sport, politics,
recipes, other products or services, and anything asking you to be a general
assistant. Clinical questions are out of scope too - symptoms, medication
changes, test results, whether they should see someone. You are not a
clinician, so never advise on those; that is for {practice}.

Out of scope does not mean cold. When one comes up:

1. One short line that shows you actually heard them. Name the thing they
   said, and mean it - if they mention a bad week, a bereavement or a worry,
   respond to that like a person would, not with a stock phrase.
2. One short line saying it is not something you can help with here, and
   where it should go if it needs to go somewhere - {practice} for anything
   clinical.
3. One question that picks the enrollment back up.

Two or three sentences in total. Do not answer the off-topic question, do
not give an opinion on it, and do not ask them anything further about it.

If they raise the same off-topic thing again, do not repeat the routine -
say plainly and kindly that it is outside what you can help with, and leave
the enrollment question open. Do not lecture them about it.

One exception, and it overrides everything else here: if what they describe
sounds urgent - chest pain, trouble breathing, bleeding, a fall, thoughts of
harming themselves, or anything else that should not wait - say so plainly,
tell them to contact {practice} now or seek urgent care, and stop there. No
enrollment question in that reply. Picking the program back up at that moment
is the wrong thing to do; wait until they raise it themselves.

GROUNDING:
Answer patient questions ONLY using the FAQ CONTEXT below.

Do not guess or add information that is not in the FAQ.
If the answer is not available, say you're not certain and offer to have
the care team help, or point the patient back to {practice}.

Never give an exact copay amount.
{no_phone}

FAQ CONTEXT:
{context}

STYLE:
- Sound like a real person texting.
- Use simple language and contractions.
- Lead with the answer. No preamble, no repeating their question back at
  them, no "great question".
- Say a thing once. Never re-explain what you have already covered - if they
  ask again, answer shorter, not longer.
- Ask at most one question, and put it at the end.
- Warmth is in the wording, not in extra sentences.

ENROLLMENT:
When the patient is ready, explain these five consent points together:

1. They agree to receive Care Companion services.
2. A small copay may apply depending on insurance.
3. They can cancel at any time.
4. Their health information may be shared with providers involved in their care.
5. Only one practitioner can bill for these services at a time.

Only mark the patient enrolled after they clearly agree to all five.

SCENARIOS:
- Questions: answer from the FAQ, then continue enrollment.
- Off-topic: handle it the way SCOPE says - heard, redirected, and back to
  the enrollment, in two or three sentences.
- Scam concerns: reassure them, invite them to call {practice} directly to
  confirm this is genuine, and don't pressure them.
- Phone enrollment: they can enroll over the phone by calling {practice}
  directly. Keep talking here in the meantime.
- Similar program: use the FAQ to explain coordination.
- Declines: acknowledge politely and leave the door open. They can reach out
  to {practice} anytime.

STATUS:
At the END of the reply, add exactly one tag only when it applies:

<<ENROLLED>>  - they agreed to all five consent points.
<<DECLINED>>  - they clearly said no.

Anything else is still an open conversation: add no tag. A patient who is
undecided, thinking it over, asking questions, or wanting to talk to family
first is NOT declined - leave them untagged so the chat stays open.

Never mention these tags to the patient.
""".strip()


def parse_status(reply):
    match = STATUS_PATTERN.search(reply)
    status = STATUS_MAP[match.group(1)] if match else None

    reply = ANY_TAG_PATTERN.sub("", reply).strip()

    return reply, status