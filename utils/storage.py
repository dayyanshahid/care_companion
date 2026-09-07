import uuid
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings

from utils.messages import messages, StorageError

_s3_client = None


def client():
    global _s3_client

    if _s3_client is None:
        if not settings.S3_BUCKET:
            raise StorageError(messages["s3BucketMissing"])

        _s3_client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT or None,
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
                request_checksum_calculation="when_required",
                response_checksum_validation="when_required",
            ),
        )

    return _s3_client


def upload(document):
    key = (
        f"{settings.S3_PROMPT_FILES_PREFIX}/{uuid.uuid4().hex}"
        f"{Path(document.name).suffix.lower()}"
    )

    try:
        document.seek(0)

        client().put_object(
            Bucket=settings.S3_BUCKET,
            Key=key,
            Body=document.read(),
            ContentType=document.content_type or "application/octet-stream",
        )
    except (BotoCoreError, ClientError) as error:
        raise StorageError(str(error)) from error
    finally:
        document.seek(0)

    return key


def delete(key):
    try:
        client().delete_object(Bucket=settings.S3_BUCKET, Key=key)
    except (BotoCoreError, ClientError) as error:
        raise StorageError(str(error)) from error


def url(key):
    try:
        return client().generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET, "Key": key},
            ExpiresIn=settings.S3_URL_TTL,
        )
    except (StorageError, BotoCoreError, ClientError):
        return ""
