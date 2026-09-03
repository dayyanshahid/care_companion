import logging
import re
from uuid import uuid4

import openai
from django.conf import settings

from api.controllers.chatbot import dal
from api.controllers.knowledge import services as knowledge
from database.serializers import ChatMessageResponseSerializer, ChatSerializer
from utils import mailer, scripts
from utils.common import build_error
from utils.enums import (
    ChatStatus,
    HttpStatus,
    MessageRole,
    Recency,
)
from utils.messages import messages

logger = logging.getLogger(__name__)


SCRIPTED = {
    "CONSENT": (scripts.CONSENT, None),
    "ENROLLED": (scripts.WELCOME, ChatStatus.enrolled),
    "DECLINED": (scripts.DECLINE, ChatStatus.declined),
    "CALLBACK": (scripts.CALLBACK, ChatStatus.callback),
    "OPTOUT": (scripts.OPT_OUT, ChatStatus.optedOut),
    "EMERGENCY": (scripts.EMERGENCY, None),
    "CRISIS": (scripts.CRISIS, None),
}

# The two that end the conversation and put a person on it.
ALERTING = ("EMERGENCY", "CRISIS")

TAG_PATTERN = re.compile(r"<<(%s)>>" % "|".join(SCRIPTED))

ANY_TAG_PATTERN = re.compile(r"<<[A-Z_]+>>")

# A patient opting out is not left to the model to notice.
OPT_OUT_WORDS = {"stop", "stopall", "unsubscribe", "cancel", "quit", "end"}

HISTORY_LIMIT = 40

CONFIG_FIELDS = (
    "patient_name",
    "patient_profile",
    "recency",
    "provider",
    "practice",
    "practice_phone",
)

client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)


class ChatServiceError(Exception):
    """A failure inside the assistant itself - OpenAI, or the FAQ behind it."""


def start_chat(tenant, patient_id):
    try:
        capture = dal.get_capture(tenant, patient_id)
    except dal.PortalError as exc:
        raise build_error(
            messages["portalUnavailable"], HttpStatus.badGateway, exc
        ) from exc

    if not capture:
        return None

    chat, is_new_record = dal.upsert_chat(tenant, capture)

    try:
        conv_id, _ = open_conversation(chat)
    except ChatServiceError as exc:
        if is_new_record:
            dal.delete_chat(chat)

        raise build_error(
            messages["assistantUnavailable"], HttpStatus.badGateway, exc
        ) from exc

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
        "messages": transcript(tenant, conv_id),
    }


def send_message(conv_id, text):
    """Answer a patient message.

    The conversation id identifies the chat on its own, so this is the one
    chat endpoint that needs no tenant: the patient follows a link, not a
    portal session.
    """
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


def list_conversations(tenant, patient_id=None):
    if patient_id and not dal.is_object_id(patient_id):
        raise build_error(messages["invalidPatientId"], HttpStatus.badRequest)

    return ChatSerializer(
        dal.find_started_chats(tenant, patient_id), many=True
    ).data


def read_conversation(tenant, ident):
    if dal.is_object_id(ident):
        return (
            messages["conversationsRetrieved"],
            list_conversations(tenant, ident),
        )

    return messages["transcriptRetrieved"], transcript(tenant, ident)


def list_patients(tenant):
    """Every remote patient this tenant's portal holds."""
    try:
        return dal.list_captures(tenant)
    except dal.PortalError as exc:
        raise build_error(
            messages["portalUnavailable"], HttpStatus.badGateway, exc
        ) from exc


def deliver_chat_link(tenant, capture, chat, conv_id):
    try:
        mailer.send_chat_link(
            capture.get("email"),
            chat.patient_name,
            chat.practice,
            chat.provider,
            conv_id,
            tenant,
        )
    except mailer.MailError as exc:
        logger.warning("Chat %s: %s", conv_id, exc)

        return False, str(exc)

    return True, ""


def transcript(tenant, conv_id):
    return [
        {
            "role": message.role,
            "text": message.text,
            "created_at": message.created_at,
        }
        for message in dal.find_messages(tenant["key"], conv_id)
    ]


def open_conversation(chat):
    conv_id = dal.add_conversation(chat, new_conversation_id())

    opener = build_opener(build_config(chat))

    dal.create_message(chat, conv_id, MessageRole.assistant, opener)

    return conv_id, opener


def reply_to(chat, conv_id, text):
    dal.create_message(chat, conv_id, MessageRole.user, text)

    config = build_config(chat)

    if is_opt_out(text):
        answer = scripts.fill(scripts.OPT_OUT, config)
        dal.set_chat_status(chat, ChatStatus.optedOut)
        dal.create_message(chat, conv_id, MessageRole.assistant, answer)

        return answer, chat.status

    context = retrieve_context(text, config)

    answer = ask_openai(
        prompt=build_system_prompt(config, context),
        history=history(chat, conv_id),
    )

    answer = apply_script(chat, answer, config)

    dal.create_message(chat, conv_id, MessageRole.assistant, answer)

    return answer, chat.status


def is_opt_out(text):
    """True when the patient's whole message is an opt-out word."""
    return "".join(c for c in text.lower() if c.isalpha()) in OPT_OUT_WORDS


def apply_script(chat, answer, config):
    match = TAG_PATTERN.search(answer)

    if not match:
        return ANY_TAG_PATTERN.sub("", answer).strip()

    tag = match.group(1)
    script, status = SCRIPTED[tag]

    if status:
        dal.set_chat_status(chat, status)

    if status is ChatStatus.enrolled:
        dal.record_consent(chat, scripts.CONSENT_VERSION)

    if tag in ALERTING:
        raised = dal.raise_alert(chat)
        logger.warning(
            "Chat %s: %s reported for patient %s, alert at %s",
            chat.conv_id, tag.lower(), chat.patient_id, raised,
        )

    return scripts.fill(script, config)


def build_config(chat):
    config = {field: getattr(chat, field) for field in CONFIG_FIELDS}
    config["care_companion_phone"] = settings.CARE_COMPANION_PHONE

    return config


def new_conversation_id():
    return f"conv_{uuid4().hex}"


def history(chat, conv_id):
    """The conversation so far, as the model reads it, oldest first."""
    messages = list(dal.find_messages(chat.tenant, conv_id))

    return [
        {"role": message.role, "content": message.text}
        for message in messages[-HISTORY_LIMIT:]
    ]


def ask_openai(prompt, history):
    try:
        response = client.responses.create(
            model=settings.OPENAI_MODEL,
            instructions=prompt,
            input=history,
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
        f"Q: {scripts.fill(chunk.question, config)}\n"
        f"A: {scripts.fill(chunk.answer, config)}"
        for chunk, _ in results
    )


def build_opener(config):
    return scripts.fill(scripts.OPENING, config)


def build_system_prompt(config, context):
    provider = config["provider"] or "your care team"
    practice = config["practice"] or "your care team"

    phone = (
        f"The practice's number is {config['practice_phone']}. Give it only "
        "when a patient needs to reach the office."
        if config.get("practice_phone")
        else "You have no phone number for anyone. Never state or invent one."
    )

    recency = {
        Recency.oneMonth: "The patient was last seen about one month ago.",
        Recency.year: "The patient was last seen about one year ago.",
    }.get(config.get("recency"), "The patient was last seen about one year ago.")

    context = context or "(No relevant FAQ was found.)"
    profile = config.get("patient_profile") or f"Name: {config['patient_name']}"

    return f"""
You are the Care Companion team's secure AI assistant, writing on behalf of
{provider}'s office at {practice}.

You help patients enroll in the Care Companion program.

WHAT YOU ARE:
You are automated software, not a person, and you never imply otherwise. You
have no name of your own and no personal history. If a patient asks who or
what they are talking to, say plainly that you are the Care Companion team's
secure automated AI assistant, texting on behalf of {provider}'s office, and
that you can have a member of the team call them whenever they would prefer
to speak with someone. Never claim to be a nurse, a member of staff, or any
named individual.

You answer at any hour, seven days a week. Business hours -
{scripts.BUSINESS_HOURS} - apply only to reaching a person, never to you.
Mention them only when a patient wants to speak with someone.

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

SCRIPTS:
This section overrides every other rule below it, including GROUNDING.

Some replies are fixed wording that has been reviewed by legal. You do not
write those. When one applies, reply with its tag ALONE and nothing else -
the reviewed text is inserted in place of your reply, so anything you write
alongside the tag is thrown away. A tag with a sentence in front of it is a
mistake; send only the tag.

<<CONSENT>>    the patient is ready to enroll and needs the consent points.
<<ENROLLED>>   they have replied yes to all seven consent points.
<<DECLINED>>   they have clearly said no to the program.
<<CALLBACK>>   they want a person to call them instead.
<<OPTOUT>>     they ask not to be contacted again.
<<EMERGENCY>>  they describe any clinical symptom or medical concern.
<<CRISIS>>     they describe thoughts of harming themselves.

Never write out the consent points, the welcome, or the emergency wording
yourself - tag it instead. Never mention these tags to the patient.

The FAQ is out of date on the consent points and lists an older, shorter set.
Ignore it. The moment a patient asks what they would be agreeing to, asks how
to enroll, or says they are ready, reply <<CONSENT>> and nothing else - do
not summarise, preview, or paraphrase the points from the FAQ or from memory.
Consent is the seven reviewed points or it is not consent.

Order matters: <<CRISIS>> and <<EMERGENCY>> override everything else, on any
turn, at any hour, whatever the conversation had reached.

CLINICAL MESSAGES:
If a patient describes a symptom, a medical concern, or anything that sounds
like it needs care - chest pain, trouble breathing, bleeding, a fall, a new
or worsening symptom - reply with <<EMERGENCY>> and nothing else. If they
describe thoughts of harming themselves, reply with <<CRISIS>> instead.

Do not assess how serious it is. Do not ask a follow-up question. Do not
mention the program in that reply. A human is alerted at the same time, so
the conversation is over: do not raise the enrollment again afterwards, even
if the patient keeps talking. Answer anything further briefly and leave it.

SCOPE:
You are here for two things only: the Care Companion program - what it is,
what it covers, what it costs, who provides it, how to join or leave - and
the patient's own record above.

Everything else is out of scope: small talk, news, weather, sport, politics,
recipes, other products or services, and anything asking you to be a general
assistant. Clinical questions are handled by the rule above, not here.

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

GROUNDING:
Answer patient questions ONLY using the FAQ CONTEXT below, except where
SCRIPTS says to send a tag instead - that always wins.

Do not guess or add information that is not in the FAQ.
If the answer is not available, say you're not certain and offer to have
the care team help, or point the patient back to {practice}.

Never give an exact copay amount.
{phone}

FAQ CONTEXT:
{context}

STYLE:
- Write simply and warmly, the way a person texting would - but never claim
  to be one.
- Use simple language and contractions.
- Lead with the answer. No preamble, no repeating their question back at
  them, no "great question".
- Say a thing once. Never re-explain what you have already covered - if they
  ask again, answer shorter, not longer.
- Ask at most one question, and put it at the end.
- Warmth is in the wording, not in extra sentences.

PERSUASION:
Your job is to get the patient enrolled. Every reply should move them a step
closer, and you should ask - don't wait to be asked.

- Make it about them. Tie the program to what is actually on their record -
  the conditions it would help them manage, their own provider, the gap since
  their last visit. A reason that fits their life beats a list of features.
- Lead with what they get, not what the program is. A dedicated licensed
  nurse who calls them, sorts out refills and appointments, and catches
  problems early.
- When they hesitate, name the worry out loud and answer that one thing from
  the FAQ - cost, time, privacy, "I'm already managing fine". Then ask again.
- End on an easy next step, not an open question. "Shall I go through what
  you'd be agreeing to?" is easier to say yes to than "so, interested?".
- If they want to think it over or ask family, that is fine - offer to cover
  the consent points now so they have everything, and leave it with them.

Honestly, though. Never pressure, guilt, or rush them. Never invent a benefit,
promise it is free, or imply their care suffers without it. Ask again at most
twice; after that, only if they bring it back up. A clear no is a no - take it
gracefully.

ENROLLMENT:
When the patient is ready, reply <<CONSENT>> and nothing else. That sends the
seven reviewed consent points.

Only reply <<ENROLLED>> after they have seen those seven points and clearly
agreed to all of them. Agreement before the points have been sent is not
consent - send <<CONSENT>> first and wait.

SCENARIOS:
- Questions: answer from the FAQ, then continue enrollment.
- Off-topic: handle it the way SCOPE says - heard, redirected, and back to
  the enrollment, in two or three sentences.
- Scam concerns: this is a fair question and worth saying so. Invite them to
  call {practice} directly to confirm the program is genuine, tell them there
  is no rush and nothing happens until they agree, and don't pressure them.
- Wants to speak to a person, or to enroll by phone instead: reply
  <<CALLBACK>> and nothing else. Hand off without resistance.
- Similar program elsewhere: use the FAQ. Different providers may enroll a
  patient in different programs; only the same program cannot be billed twice
  in the same period.
- Declines: reply <<DECLINED>> and nothing else.
""".strip()