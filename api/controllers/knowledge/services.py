"""Knowledge base for the Care Companion FAQ (the RAG layer).

Ingestion parses the FAQ .docx into Q&A chunks, embeds each with OpenAI
(text-embedding-3-small by default), and stores them in Qdrant Cloud.
Retrieval embeds a query and asks Qdrant for the nearest chunks - the search
runs in Qdrant's index, so nothing is scored in Python here.

Qdrant holds both the vector and the chunk's text, as the point's payload, so
the FAQ has no MongoDB collection of its own.
"""
import re
from dataclasses import dataclass

import openai
from django.conf import settings
from qdrant_client import QdrantClient, models

_QA_RE = re.compile(r"^Q\d+\.\s*", re.IGNORECASE)
_SECTION_RE = re.compile(r"^(\d+)\.\s+(.*)")

_openai_client = None
_qdrant_client = None


class KnowledgeError(Exception):
    """Raised when parsing fails, or a provider is unavailable."""


@dataclass
class Chunk:
    """One retrieved FAQ entry. Reads like the model row it replaced."""

    id: str
    category: str
    question: str
    answer: str


# --- Ingestion --------------------------------------------------------------

def ingest_faq(path):
    """Parse the FAQ .docx, embed each Q&A, and replace the stored chunks."""
    entries = parse_faq(path)
    if not entries:
        raise KnowledgeError(f"No FAQ entries found in {path}.")

    vectors = _embed(
        [f"{e['category']} — {e['question']}\n{e['answer']}" for e in entries]
    )

    client = _qdrant()

    # A fresh collection each time, so a re-ingest cannot leave stale answers
    # behind. The upsert is one call, so the gap is as short as it can be.
    try:
        client.delete_collection(settings.QDRANT_COLLECTION)
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=models.VectorParams(
                size=settings.EMBEDDING_DIM,
                distance=models.Distance.COSINE,
            ),
        )
        client.upsert(
            collection_name=settings.QDRANT_COLLECTION,
            points=[
                models.PointStruct(id=index, vector=vector, payload=entry)
                for index, (entry, vector) in enumerate(zip(entries, vectors))
            ],
            wait=True,
        )
    except Exception as exc:
        raise KnowledgeError(f"Qdrant rejected the ingest: {exc}") from exc

    return len(entries)


def parse_faq(path):
    """Extract Q&A entries from the FAQ .docx.

    The FAQ stores each section header and each question in its own table.
    A section cell looks like "3. Financial Coverage..." followed by
    "5 questions"; a question cell starts with "Qn.".
    """
    from docx import Document  # imported here so parsing is optional at runtime

    document = Document(path)
    entries = []
    category = "General"

    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                paragraphs = [p.text.strip() for p in cell.paragraphs if p.text.strip()]
                if not paragraphs:
                    continue

                head = paragraphs[0]
                section = _SECTION_RE.match(head)
                if section and "question" in paragraphs[-1].lower():
                    category = section.group(2).strip()
                    continue

                if _QA_RE.match(head):
                    question = _QA_RE.sub("", head).strip()
                    answer = " ".join(paragraphs[1:]).strip()
                    if question and answer:
                        entries.append(
                            {"category": category, "question": question, "answer": answer}
                        )
    return entries


# --- Retrieval --------------------------------------------------------------

def retrieve(query, top_k):
    """Return the top_k (chunk, score) pairs most relevant to the query."""
    query_vector = _embed([query])[0]

    try:
        found = _qdrant().query_points(
            collection_name=settings.QDRANT_COLLECTION,
            query=query_vector,
            limit=top_k,
            with_payload=True,
        ).points
    except Exception as exc:
        raise KnowledgeError(f"Qdrant could not be searched: {exc}") from exc

    return [
        (
            Chunk(
                id=str(point.id),
                category=point.payload.get("category", ""),
                question=point.payload.get("question", ""),
                answer=point.payload.get("answer", ""),
            ),
            point.score,
        )
        for point in found
    ]


def all_chunks(limit=1000):
    """Every stored chunk, vectors left behind. For checks and inspection."""
    try:
        points, _ = _qdrant().scroll(
            collection_name=settings.QDRANT_COLLECTION,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
    except Exception as exc:
        raise KnowledgeError(f"Qdrant could not be read: {exc}") from exc

    return [
        Chunk(
            id=str(point.id),
            category=point.payload.get("category", ""),
            question=point.payload.get("question", ""),
            answer=point.payload.get("answer", ""),
        )
        for point in points
    ]


def count_chunks():
    """How many chunks are stored. 0 also means the collection is not there."""
    try:
        client = _qdrant()

        if not client.collection_exists(settings.QDRANT_COLLECTION):
            return 0

        return client.count(settings.QDRANT_COLLECTION, exact=True).count
    except KnowledgeError:
        raise
    except Exception as exc:
        raise KnowledgeError(f"Qdrant could not be reached: {exc}") from exc


# --- Clients ----------------------------------------------------------------

def _qdrant():
    global _qdrant_client

    if _qdrant_client is None:
        if not settings.QDRANT_URL:
            raise KnowledgeError("QDRANT_URL is not configured.")

        _qdrant_client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY or None,
            timeout=30,
        )

    return _qdrant_client


def _embed(texts):
    try:
        response = _client().embeddings.create(input=texts, model=settings.EMBEDDING_MODEL)
        return [item.embedding for item in response.data]
    except Exception as exc:  # network, auth, rate limit, etc.
        raise KnowledgeError(str(exc)) from exc


def _client():
    global _openai_client
    if _openai_client is None:
        if not settings.OPENAI_API_KEY:
            raise KnowledgeError("OPENAI_API_KEY is not configured.")
        _openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client
