"""Turning an uploaded document into the text the prompt can carry.

The bytes go to S3 unread; this is the part the assistant sees.
"""
import io
from pathlib import Path

import docx

from utils.messages import messages, DocumentError

PLAIN_SUFFIXES = {".txt", ".md"}


def read_text(document):
    suffix = Path(document.name).suffix.lower()

    document.seek(0)
    raw = document.read()
    document.seek(0)

    if suffix == ".docx":
        return _docx_text(raw)

    if suffix in PLAIN_SUFFIXES:
        return raw.decode("utf-8", errors="replace").strip()

    raise DocumentError(
        messages["fileTypeUnsupported"].format(name=document.name)
    )


def _docx_text(raw):
    try:
        opened = docx.Document(io.BytesIO(raw))
    except Exception as error:
        raise DocumentError(str(error)) from error

    lines = [paragraph.text.strip() for paragraph in opened.paragraphs]

    lines += [
        cell.text.strip()
        for table in opened.tables
        for row in table.rows
        for cell in row.cells
    ]

    return "\n".join(line for line in lines if line)
