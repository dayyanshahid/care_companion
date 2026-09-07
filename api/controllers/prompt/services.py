"""The prompt the assistant runs on, and the documents behind it.

The database is the only source: nothing is shipped on disk, so until a prompt
is stored the assistant has nothing to send and says so.

An update overwrites the single prompt record and appends whatever files came
with it. A delete removes one document - from S3 and from the record - and
leaves every other document standing.
"""
from api.controllers.prompt import dal
from database.serializers import SystemPromptResponseSerializer
from utils import documents, storage
from utils.common import build_error
from utils.enums import HttpStatus
from utils.messages import messages, DocumentError, StorageError


def current():
    """What the assistant should send. There is no prompt but a stored one."""
    prompt = dal.find_prompt()

    if prompt is None:
        raise build_error(
            messages["promptNotConfigured"], HttpStatus.serviceUnavailable
        )

    return {
        "body": prompt.body,
        "knowledge": "\n\n".join(
            record.text for record in dal.find_files() if record.text
        ),
    }


def read():
    prompt = dal.find_prompt()

    return SystemPromptResponseSerializer(
        {
            "system_prompt": prompt.body if prompt else "",
            "files": [_file_data(record) for record in dal.find_files()],
        }
    ).data


def update(payload):
    body = payload["system_prompt"].strip()
    uploads = payload["files"]

    if not body and not uploads:
        raise build_error(messages["nothingToUpdate"])

    # Nothing is written until every document has been read and stored. A
    # refused file type or an unreachable bucket must leave the prompt in
    # force exactly as it was, rather than half-applying the update.
    texts = _read_all(uploads)
    keys = _upload_all(uploads)

    for document, text, key in zip(uploads, texts, keys):
        dal.create_file(
            name=document.name,
            s3_key=key,
            content_type=document.content_type or "",
            size=document.size,
            text=text,
        )

    if body:
        dal.save_prompt(body, payload["updated_by"])

    return read()


def remove(file_id):
    record = dal.find_file(file_id)

    if record is None:
        raise build_error(messages["promptFileNotFound"], HttpStatus.notFound)

    try:
        storage.delete(record.s3_key)
    except StorageError as error:
        raise build_error(
            messages["storageUnavailable"], HttpStatus.badGateway, error
        ) from error

    dal.delete_file(record)

    return read()


def _read_all(uploads):
    try:
        return [documents.read_text(document) for document in uploads]
    except DocumentError as error:
        raise build_error(
            str(error), HttpStatus.badRequest, error
        ) from error


def _upload_all(uploads):
    """Every document reaches the bucket, or none of them stays there."""
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
    """Undo one upload. The failure being reported is the one that matters."""
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
