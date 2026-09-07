from api.controllers.prompt import dal
from database.serializers import SystemPromptResponseSerializer
from utils import documents, storage
from utils.common import build_error
from utils.enums import HttpStatus
from utils.messages import messages, DocumentError, StorageError


def current():
    prompt = dal.find_any_prompt()

    if prompt is None or not prompt.body.strip():
        raise build_error(
            messages["promptNotConfigured"], HttpStatus.serviceUnavailable
        )

    return {
        "body": prompt.body,
        "name": prompt.chatbot_name,
        "knowledge": "\n\n".join(
            record.text for record in dal.find_all_files() if record.text
        ),
    }


def read(tennet_id):
    prompt = dal.find_prompt(tennet_id)

    return SystemPromptResponseSerializer(
        {
            "system_prompt": prompt.body if prompt else "",
            "chatbot_name": prompt.chatbot_name if prompt else "",
            "tennet_id": str(tennet_id),
            "files": [
                _file_data(record) for record in dal.find_files(tennet_id)
            ],
        }
    ).data


def update(payload):
    tennet_id = payload["tennet_id"]
    body = payload["system_prompt"].strip()
    name = payload["chatbot_name"].strip()
    uploads = payload["files"]

    if not body and not name and not uploads:
        raise build_error(messages["nothingToUpdate"])

    texts = _read_all(uploads)
    keys = _upload_all(uploads)

    for document, text, key in zip(uploads, texts, keys):
        dal.create_file(
            tennet_id=tennet_id,
            name=document.name,
            s3_key=key,
            content_type=document.content_type or "",
            size=document.size,
            text=text,
        )

    changes = {}

    if body:
        changes["body"] = body

    if name:
        changes["chatbot_name"] = name

    if changes:
        changes["updated_by"] = payload["updated_by"]
        dal.save_prompt(tennet_id, changes)

    return read(tennet_id)


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

    tennet_id = record.tennet_id
    dal.delete_file(record)

    return read(tennet_id)


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
