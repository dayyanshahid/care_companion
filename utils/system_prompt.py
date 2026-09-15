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
    return re.sub(r"(?<!\n)\n(?!\n)[ \t]*", " ", text)