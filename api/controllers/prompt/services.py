import hashlib

from api.controllers.prompt import dal
from database.serializers import SystemPromptResponseSerializer
from django.conf import settings

from utils import documents, embeddings, storage
from utils.common import build_error
from utils.enums import HttpStatus
from utils.messages import (
    messages,
    DocumentError,
    EmbeddingError,
    StorageError,
)


def current(tenant_id, query=""):
    prompt = dal.find_prompt(tenant_id)

    if prompt is None or not prompt.body.strip():
        raise build_error(
            messages["promptNotConfigured"], HttpStatus.serviceUnavailable
        )

    return {
        "body": prompt.body,
        "name": prompt.chatbot_name,
        "knowledge": retrieve(tenant_id, query),
    }


def retrieve(tenant_id, query):
    if not query.strip():
        return ""

    chunks = list(dal.find_chunks(tenant_id))

    if not chunks:
        return ""

    try:
        vector = embeddings.embed([query])[0]
    except EmbeddingError as error:
        raise build_error(
            messages["documentsUnavailable"], HttpStatus.badGateway, error
        ) from error

    best = embeddings.rank(
        vector, chunks, settings.RAG_TOP_K, settings.RAG_MIN_SCORE
    )

    return "\n\n".join(chunk.text for chunk, _ in best)


def read(tenant_id):
    prompt = dal.find_prompt(tenant_id)

    return SystemPromptResponseSerializer(
        {
            "system_prompt": prompt.body if prompt else "",
            "chatbot_name": prompt.chatbot_name if prompt else "",
            "tenant_id": str(tenant_id),
            "files": [
                _file_data(record) for record in dal.find_files(tenant_id)
            ],
        }
    ).data


def update(payload):
    tenant_id = payload["tenant_id"]
    body = payload["system_prompt"].strip()
    name = payload["chatbot_name"].strip()
    uploads = payload["files"]

    if not body and not name and not uploads:
        raise build_error(messages["nothingToUpdate"])

    texts = _read_all(uploads)
    _sync_files(tenant_id, uploads, texts)

    changes = {}

    if body:
        changes["body"] = body

    if name:
        changes["chatbot_name"] = name

    if changes:
        changes["updated_by"] = payload["updated_by"]
        dal.save_prompt(tenant_id, changes)

    return read(tenant_id)


def _sync_files(tenant_id, uploads, texts):
    stored = {}

    for record in dal.find_files(tenant_id):
        stored.setdefault(record.name, []).append(record)

    incoming = []

    for document, text in zip(uploads, texts):
        previous = stored.pop(document.name, [])
        kept = previous[0] if previous else None

        for spare in previous[1:]:
            _drop(spare)

        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()

        if kept is not None and kept.content_hash == digest:
            continue

        incoming.append((document, text, digest, kept))

    keys = _upload_all([item[0] for item in incoming])

    try:
        pieces = _embed_all([item[1] for item in incoming])
    except Exception:
        for key in keys:
            _discard(key)
        raise

    for (document, text, digest, kept), key, chunks in zip(incoming, keys, pieces):
        if kept is None:
            record = dal.create_file(
                tenant_id=tenant_id,
                name=document.name,
                s3_key=key,
                content_type=document.content_type or "",
                size=document.size,
                text=text,
                content_hash=digest,
            )
        else:
            replaced = kept.s3_key
            record = dal.update_file(
                kept, key, document.content_type or "", document.size,
                text, digest,
            )
            dal.delete_chunks(record.id)
            _discard(replaced)

        dal.create_chunks(tenant_id, record.id, chunks)

    for records in stored.values():
        for record in records:
            _drop(record)


def _drop(record):
    _discard(record.s3_key)
    dal.delete_chunks(record.id)
    dal.delete_file(record)


def _embed_all(texts):
    per_document = [documents.chunk(text) for text in texts]
    flat = [piece for pieces in per_document for piece in pieces]

    if not flat:
        return [[] for _ in texts]

    try:
        vectors = embeddings.embed(flat)
    except EmbeddingError as error:
        raise build_error(
            messages["documentsUnavailable"], HttpStatus.badGateway, error
        ) from error

    out, cursor = [], 0

    for pieces in per_document:
        out.append(list(zip(pieces, vectors[cursor:cursor + len(pieces)])))
        cursor += len(pieces)

    return out


def _read_all(uploads):
    try:
        return [documents.read_text(document) for document in uploads]
    except DocumentError as error:
        raise build_error(
            str(error), HttpStatus.badRequest, error
        ) from error


def _upload_all(uploads):
    keys = []

    try:
        for document in uploads:
            keys.append(storage.upload(document))
    except StorageError as error:
        for key in keys:
            _discard(key)

        raise build_error(
            messages["storageUnavailable"], HttpStatus.badGateway, error
        ) from error

    return keys


def _discard(key):
    try:
        storage.delete(key)
    except StorageError:
        pass


def _file_data(record):
    return {
        "id": str(record.id),
        "name": record.name,
        "content_type": record.content_type,
        "size": record.size,
        "url": storage.url(record.s3_key),
        "created_at": record.created_at,
    }