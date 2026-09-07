"""Turning an uploaded document into text, and text into chunks.

The bytes go to S3 unread; this is the part the assistant sees. Reading keeps
the document in its own order and keeps a table row whole, because a question
and its answer usually sit in the same row and must not be split apart.
"""
import io
import re
from pathlib import Path

import docx
from docx.document import Document as DocxDocument
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph

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

    if suffix in PLAIN_SUFFIXES:
        return raw.decode("utf-8", errors="replace").strip()

    raise DocumentError(
        messages["fileTypeUnsupported"].format(name=document.name)
    )


def chunk(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Split text into overlapping pieces, breaking between lines only.

    A line is the smallest thing worth keeping whole - for a table-shaped
    document that is one row, question and answer together. A line longer than
    `size` is left oversized rather than cut mid-sentence.
    """
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
    """The document as lines no longer than a chunk.

    A line usually is the natural unit, but a document can arrive as one
    unbroken block - prose exported without newlines, say. Such a line is cut
    on sentences, and a sentence longer than a chunk is cut where it must be,
    so nothing ever exceeds what the embedding model will take.
    """
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
    """Hold back a trailing question or heading; its answer is the next line."""
    head, newline, last = text.rpartition("\n")

    if newline and last.endswith(("?", ":")):
        return head, last

    return text, ""


def _tail(text, overlap):
    """The end of a chunk, carried into the next one so context survives."""
    if overlap <= 0:
        return ""

    carried = text[-overlap:]
    _, newline, rest = carried.partition("\n")

    return rest if newline else carried


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
            # A row is one line: "Q1. ...  |  the answer" stays together, and
            # repeated merged cells are collapsed.
            cells = [
                cell
                for index, cell in enumerate(cells)
                if cell and cell not in cells[:index]
            ]

            if cells:
                lines.append(" | ".join(cells))

    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def _blocks(parent):
    """Paragraphs and tables in the order the document puts them."""
    element = parent.element.body if isinstance(parent, DocxDocument) else parent._tc

    for child in element.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)
