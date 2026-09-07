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

    # Read every document before writing anything, so an unsupported file is
    # refused outright rather than half-applied.
    texts = _read_all(uploads)

    if body:
        dal.save_prompt(body, payload["updated_by"])

    for document, text in zip(uploads, texts):
        _store(document, text)

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


def _store(document, text):
    try:
        key = storage.upload(document)
    except StorageError as error:
        raise build_error(
            messages["storageUnavailable"], HttpStatus.badGateway, error
        ) from error

    return dal.create_file(
        name=document.name,
        s3_key=key,
        content_type=document.content_type or "",
        size=document.size,
        text=text,
    )


def _file_data(record):
    return {
        "id": str(record.id),
        "name": record.name,
        "content_type": record.content_type,
        "size": record.size,
        "url": storage.url(record.s3_key),
        "created_at": record.created_at,
    }
