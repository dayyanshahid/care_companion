"""Embedding text, and comparing the vectors.

Similarity is scored here in Python rather than by the database: this MongoDB
has no vector index, and at a few hundred chunks a full scan costs less than
reaching for one would.
"""
from math import sqrt

import openai
from django.conf import settings

from utils.messages import messages, EmbeddingError

BATCH = 96

_embedding_client = None


def client():
    global _embedding_client

    if _embedding_client is None:
        if not settings.OPENAI_API_KEY:
            raise EmbeddingError(messages["openaiKeyMissing"])

        _embedding_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

    return _embedding_client


def embed(texts):
    """Vectors for these texts, in the order they were given."""
    if not texts:
        return []

    api = client()
    vectors = []

    for start in range(0, len(texts), BATCH):
        window = texts[start:start + BATCH]

        try:
            response = api.embeddings.create(
                input=window,
                model=settings.EMBEDDING_MODEL,
                dimensions=settings.EMBEDDING_DIMENSIONS,
            )
        except Exception as error:
            raise EmbeddingError(str(error)) from error

        vectors.extend(item.embedding for item in response.data)

    return vectors


def cosine(left, right):
    """Similarity of two vectors, 0 when either has no length."""
    if not left or not right:
        return 0.0

    dot = sum(a * b for a, b in zip(left, right))
    size = sqrt(sum(a * a for a in left)) * sqrt(sum(b * b for b in right))

    return dot / size if size else 0.0


def rank(vector, chunks, top_k):
    """The top_k chunks most like `vector`, best first."""
    scored = sorted(
        ((chunk, cosine(vector, chunk.embedding)) for chunk in chunks),
        key=lambda pair: pair[1],
        reverse=True,
    )

    return scored[:top_k]
