import re
from pathlib import Path

PROMPT = (Path(__file__).parent / "system_prompt.md").read_text(encoding="utf-8")

PLACEHOLDERS = {
    "[Patient Name]": "patient_name",
    "[Provider name]": "provider",
    "[Practice name]": "practice",
    "[Practice Phone Number]": "practice_phone",
    "[Care Companion number]": "care_companion_phone",
}


def fill(values):
    text = PROMPT

    for placeholder, field in PLACEHOLDERS.items():
        value = (values.get(field) or "").strip()

        if value:
            text = text.replace(placeholder, value)

    if not (values.get("patient_name") or "").strip():
        text = re.sub(r",?\s*\[Patient Name\]", "", text)

    return text


def templates(prompt):
    section = prompt.split("## 6. REVIEWED WORDING")[1].split("\n## 7.")[0]
    blocks = re.split(r"\n### ", section)[1:]

    return {
        name.strip().upper(): _unwrap(body.strip())
        for name, _, body in (block.partition("\n") for block in blocks)
    }


def _unwrap(text):
    return re.sub(r"(?<!\n)\n(?!\n|\d+\. )[ \t]*", " ", text)