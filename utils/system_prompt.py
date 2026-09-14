import re

PLACEHOLDERS = {
    "[Patient Name]": "patient_name",
    "[Provider name]": "provider",
    "[Practice name]": "practice",
    "[Practice Phone Number]": "practice_phone",
    "[Care Companion number]": "care_companion_phone",
}


def fill(body, values):
    text = body

    for placeholder, field in PLACEHOLDERS.items():
        value = (values.get(field) or "").strip()

        if value:
            text = text.replace(placeholder, value)
        elif placeholder == "[Patient Name]":
            text = re.sub(r",?\s*\[Patient Name\]", "", text)
        else:
            text = _drop(text, placeholder)

    return text


def _drop(text, placeholder):
    """No value for this placeholder, so the sentence carrying it does not go out.

    Section 6 wording is never written by the model - it sends a label and the
    reviewed text is substituted in afterwards - so a bracket still standing
    here is one a patient reads. Rule 10 drops the sentence, never invents a
    value. A name is the exception and is handled above: dropping the sentence
    would take the whole greeting with it.
    """
    lines = []

    for line in text.split("\n"):
        if placeholder in line:
            sentences = re.findall(r"[^.]*\.[ \t]*|[^.]+$", line)
            line = "".join(s for s in sentences if placeholder not in s).rstrip()

        lines.append(line)

    return "\n".join(lines)


def templates(prompt):
    _, marker, rest = prompt.partition("## 6. REVIEWED WORDING")

    if not marker:
        return {}

    blocks = re.split(r"\n### ", rest.split("\n## 7.")[0])[1:]

    return {
        name.strip().upper(): _unwrap(body.strip())
        for name, _, body in (block.partition("\n") for block in blocks)
    }


def _unwrap(text):
    """One paragraph per reviewed message.

    The seven consent points used to keep their line breaks. CONSENT was then
    the only message carrying newlines, and the only one that never reached a
    handset - the opening outreach is the same length, has none, and arrives.
    """
    return re.sub(r"(?<!\n)\n(?!\n)[ \t]*", " ", text)
