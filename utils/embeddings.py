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
    if not left or not right:
        return 0.0

    dot = sum(a * b for a, b in zip(left, right))
    size = sqrt(sum(a * a for a in left)) * sqrt(sum(b * b for b in right))

    return dot / size if size else 0.0


def rank(vector, chunks, top_k, floor=0.0):
    scored = [
        pair
        for pair in ((chunk, cosine(vector, chunk.embedding)) for chunk in chunks)
        if pair[1] >= floor
    ]

    scored.sort(key=lambda pair: pair[1], reverse=True)

    return scored[:top_k]
