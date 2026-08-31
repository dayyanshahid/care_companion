import re
import openai
from django.conf import settings
from api.controllers.knowledge import services as knowledge
from database.models import Message


PLACEHOLDERS = {
    "[Provider name]": "provider",
    "[Practice name]": "practice",
    "[Patient Name]": "patient_name",
}

# Emma holds no phone numbers, so the FAQ's number placeholders are reworded
# to point at the practice rather than left standing in the text.
PHONE_FALLBACKS = (
    (", [Care Companion number]", ""),
    ("[Care Companion number]", "the Care Companion number"),
    ("[Practice Phone Number]", "the practice"),
    ("[Practice phone]", "the practice"),
)

STATUS_MAP = {
    "ENROLLED": "enrolled",
    "DECLINED": "declined",
    "CALLBACK": "callback",
}

STATUS_PATTERN = re.compile(r"<<(ENROLLED|DECLINED|CALLBACK)>>")

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
    pass

def start_chat(chat):
    """Open a chat and write Emma's first message."""
    chat.conv_id = create_openai_conversation()
    chat.save(update_fields=["conv_id", "updated_at"])

    config = build_config(chat)
    opener = build_opener(config)

    save_message(chat, "assistant", opener)

    # Seed the OpenAI conversation with the opener so it has the same history.
    ask_openai(
        conv_id=chat.conv_id,
        prompt=build_system_prompt(config, ""),
        text=opener,
    )

    return opener


def reply_to(chat, text):
    """Answer one patient message. Returns the reply and the chat's status."""
    save_message(chat, "user", text)

    config = build_config(chat)
    context = retrieve_context(text, config)

    answer = ask_openai(
        conv_id=chat.conv_id,
        prompt=build_system_prompt(config, context),
        text=text,
    )

    answer, status = parse_status(answer)

    save_message(chat, "assistant", answer)

    if status:
        chat.status = status
        chat.save(update_fields=["status", "updated_at"])

    return answer, chat.status


def build_config(chat):
    """The patient details every prompt is built from."""
    return {field: getattr(chat, field) for field in CONFIG_FIELDS}


def create_openai_conversation():
    try:
        return client.conversations.create().id
    except Exception as exc:
        raise ChatServiceError(str(exc)) from exc


def ask_openai(conv_id, prompt, text):
    """One turn against the OpenAI conversation. Returns its reply text."""
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
        "onemonth": (
            f"{opening} It's been about a month since your last visit, and "
            f"{asked} wanted us to check in about our Care Companion program."
        ),
        "year": (
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


def phone_rule(config):
    """Emma has no number to give, and must not invent one."""
    practice = config["practice"] or "the practice"

    return (
        "Never state a phone number. You do not have one, so do not "
        f'invent one - refer to "{practice}" or "the office" instead.'
    )


def build_system_prompt(config, context):
    provider = config["provider"] or "your care team"
    practice = config["practice"] or "your care team"

    recency = {
        "onemonth": "The patient was last seen about one month ago.",
        "year": "The patient was last seen about one year ago.",
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

GROUNDING:
Answer patient questions ONLY using the FAQ CONTEXT below.

Do not guess or add information that is not in the FAQ.
If the answer is not available, say you're not certain and offer to have
the care team help, or point the patient back to {practice}.

Never give an exact copay amount.
{phone_rule(config)}

FAQ CONTEXT:
{context}

STYLE:
- Sound like a real person texting.
- Use simple language and contractions.
- Keep replies to 1-3 short sentences.
- Answer the patient's question first.
- Then gently move the conversation forward.

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
- Scam concerns: reassure them, invite them to call {practice} directly to
  confirm this is genuine, and don't pressure them.
- Phone enrollment: offer a program-specialist callback within the next business day.
- Similar program: use the FAQ to explain coordination.
- Declines: acknowledge politely and leave the door open. They can reach out
  to {practice} anytime.

STATUS:
At the END of the reply, add exactly one tag only when it applies:

<<ENROLLED>>
<<CALLBACK>>
<<DECLINED>>

Otherwise add no tag.

Never mention these tags to the patient.
""".strip()


def save_message(chat, role, text):
    """One turn of the transcript, against the chat it belongs to."""
    Message.objects.create(
        remoteenrollement_id=chat.id,
        conversation_id=chat.conv_id,
        role=role,
        text=text,
    )


def parse_status(reply):
    match = STATUS_PATTERN.search(reply)

    if not match:
        return reply.strip(), None

    status = STATUS_MAP[match.group(1)]
    reply = STATUS_PATTERN.sub("", reply).strip()

    return reply, status