import io
import re
from pathlib import Path

import docx
from docx.document import Document as DocxDocument
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph
from pypdf import PdfReader

from utils.messages import messages, DocumentError

PLAIN_SUFFIXES = {".txt", ".md"}

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 150


def read_text(document):
    suffix = Path(document.name).suffix.lower()

    document.seek(0)
    raw = document.read()
    document.seek(0)

    if suffix == ".docx":
        return _docx_text(raw)

    if suffix == ".pdf":
        return _pdf_text(raw)

    if suffix in PLAIN_SUFFIXES:
        return raw.decode("utf-8", errors="replace").strip()

    raise DocumentError(
        messages["fileTypeUnsupported"].format(name=document.name)
    )


def chunk(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks = []
    current = ""

    for line in _lines(text, size):
        if current and len(current) + len(line) + 1 > size:
            head, lead = _split_lead(current)
            chunks.append(head)
            carried = _tail(head, overlap)
            current = f"{carried}\n{lead}".strip() if lead else carried

        current = f"{current}\n{line}" if current else line

    if current.strip():
        chunks.append(current)

    return chunks


def _lines(text, size):
    for line in (line.strip() for line in text.splitlines()):
        if not line:
            continue

        if len(line) <= size:
            yield line
            continue

        current = ""

        for sentence in re.split(r"(?<=[.!?])\s+", line):
            while len(sentence) > size:
                yield sentence[:size]
                sentence = sentence[size:]

            if current and len(current) + len(sentence) + 1 > size:
                yield current
                current = sentence
            else:
                current = f"{current} {sentence}" if current else sentence

        if current:
            yield current


def _split_lead(text):
    head, newline, last = text.rpartition("\n")

    if newline and last.endswith(("?", ":")):
        return head, last

    return text, ""


def _tail(text, overlap):
    if overlap <= 0:
        return ""

    carried = text[-overlap:]
    _, newline, rest = carried.partition("\n")

    return rest if newline else carried


def _pdf_text(raw):
    try:
        reader = PdfReader(io.BytesIO(raw))
    except Exception as error:
        raise DocumentError(str(error)) from error

    pages = [(page.extract_text() or "") for page in reader.pages]

    return re.sub(
        r"\n{3,}", "\n\n", "\n".join(pages)
    ).strip()


def _docx_text(raw):
    try:
        opened = docx.Document(io.BytesIO(raw))
    except Exception as error:
        raise DocumentError(str(error)) from error

    lines = []

    for block in _blocks(opened):
        if isinstance(block, Paragraph):
            if block.text.strip():
                lines.append(block.text.strip())
            continue

        for row in block.rows:
            cells = [cell.text.strip() for cell in row.cells]
            cells = [
                cell
                for index, cell in enumerate(cells)
                if cell and cell not in cells[:index]
            ]

            if cells:
                lines.append(" | ".join(cells))

    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def _blocks(parent):
    element = parent.element.body if isinstance(parent, DocxDocument) else parent._tc

    for child in element.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)