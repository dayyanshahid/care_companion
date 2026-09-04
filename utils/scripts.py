import re

BUSINESS_HOURS = "Monday to Friday, 8:00 AM to 5:00 PM CST"


OPENING = (
    "Hi [Patient Name], this is the Care Companion team's secure AI "
    "assistant, texting on behalf of [Provider name] at [Practice name]. "
    "[Provider name]'s office is offering the Care Companion program to "
    "support you between your clinic visits. The program will assign you a "
    "dedicated licensed nurse as your care manager for; health questions, "
    "medication review, appointment scheduling, dietary guidance, and vitals "
    "monitoring. The program is covered by Medicare, Medicare Advantage, and "
    "most commercial insurance. Reply YES if you'd like to hear more, or just "
    "reply with any question and I'll answer within a few minutes. I can also "
    "arrange for someone from our team to call you."
)

CONSENT = (
    "Before we enroll you, [Patient Name], please read these seven points and "
    "reply YES to confirm you understand and agree to all of them:\n"
    "1. Our care team will support you between visits, on behalf of "
    "[Provider name].\n"
    "2. There may be a copay or deductible, depending on your insurance plan.\n"
    "3. Only one practitioner can bill for this service in a given period.\n"
    "4. Your health information may be shared with authorized Care Companion "
    "providers.\n"
    "5. Participation is voluntary and you can cancel at any time.\n"
    "6. If you receive a monitoring device and later decide against it, it is "
    "your responsibility to return it to the office within 7 days.\n"
    "7. You agree to receive program communications by phone, email, and text.\n"
    "Reply YES to confirm all seven."
)

WELCOME = (
    "Welcome to the Care Companion program, [Patient Name]. Your dedicated "
    "care manager will call you within two business days from phone number: "
    "[Care Companion number], during normal business hours (" + BUSINESS_HOURS
    + "). Please save that number as \"Care Companion\" so you can recognize "
    "when we call. You don't need to call us; your care manager will reach out "
    "to you.\n"
    "If you have an urgent medical concern at any time, call 911 or go to your "
    "nearest emergency room. This number is not monitored for emergencies."
)

DECLINE = (
    "Thank you for letting us know, [Patient Name]. We won't contact you about "
    "this program again. If you change your mind at any point, just mention it "
    "to [Provider name]'s office at your next visit and they'll get the "
    "process started again. Take care."
)

CALLBACK = (
    "Happy to arrange that, [Patient Name]. A member of our Care Companion "
    "team will call you on the next business day during normal business hours "
    "(" + BUSINESS_HOURS + "). If anything comes up before then, "
    "[Provider name]'s office can always reach us on your behalf. Reply STOP "
    "to opt out of future messages."
)

EMERGENCY = (
    "If this is a medical emergency, please call 911 now or go to your nearest "
    "emergency room. This text line is not monitored for emergencies and "
    "cannot help with urgent medical concerns.\n"
    "For anything non-urgent, please call [Provider name]'s office at "
    "[Practice Phone Number]."
)

# The document escalates self-harm separately, with 988 alongside 911.
CRISIS = (
    "If you are thinking about harming yourself, please call or text 988 now "
    "to reach the Suicide and Crisis Lifeline, or call 911 or go to your "
    "nearest emergency room. This text line is not monitored for emergencies "
    "and cannot help with urgent concerns.\n"
    "For anything non-urgent, please call [Provider name]'s office at "
    "[Practice Phone Number]."
)

OPT_OUT = (
    "You're opted out, [Patient Name]. We won't message you about the Care "
    "Companion program again. If you change your mind, just mention it to "
    "[Provider name]'s office at your next visit."
)

SUPERSEDED_FAQ = (
    "what do i need to do to actually enroll",
    "what am i agreeing to when i enroll",
)

def supersedes(question):
    """True when the reviewed scripts replace this FAQ entry."""
    asked = "".join(c for c in question.lower() if c.isalnum() or c == " ").strip()

    return any(asked.startswith(entry) for entry in SUPERSEDED_FAQ)


# Everything a script can name, and where each value comes from.
PLACEHOLDERS = {
    "[Patient Name]": "patient_name",
    "[Provider name]": "provider",
    "[Practice name]": "practice",
    "[Care Companion number]": "care_companion_phone",
    "[Practice Phone Number]": "practice_phone",
}

EMPTY_CLAUSES = {
    "[Care Companion number]": (
        " from phone number: [Care Companion number], during normal business hours",
        " from phone number: [Care Companion number]",
        ", [Care Companion number]",
        ' Please save that number as "Care Companion" so you can recognize'
        " when we call.",
    ),
    "[Practice Phone Number]": (
        " at [Practice Phone Number]",
    ),
}

_LEFTOVER = re.compile(r"\s*\[[A-Za-z ]+\]")


def fill(text, values):
    for placeholder, field in PLACEHOLDERS.items():
        value = (values.get(field) or "").strip()

        if value:
            text = text.replace(placeholder, value)
            continue

        for clause in EMPTY_CLAUSES.get(placeholder, ()):
            text = text.replace(clause, "")

    return _LEFTOVER.sub("", text)