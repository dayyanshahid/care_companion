import logging
import re

from django.conf import settings
from pymongo import MongoClient
from pymongo.uri_parser import parse_uri

from utils.messages import messages

logger = logging.getLogger(__name__)

COLLECTION = "tenants"
ACTIVE = {"deletedAt": None}

_client = None
_by_slug = None


class TenantError(Exception):
    """Raised when the registry cannot be read, or a record is unusable."""


def slug(value):
    value = (value or "").strip().lower()
    value = re.sub(r"^[a-z][a-z0-9+.-]*://", "", value)  # scheme
    host, _, port = value.split("/")[0].partition(":")   # path, then port

    label = host.split(".")[0]                           # first host label

    return f"{label}:{port}" if label and port else label


def find(subdomain):
    wanted = slug(subdomain)

    if not wanted:
        return None

    tenant = _map().get(wanted)

    if tenant is None:
        tenant = _map(reload=True).get(wanted)

    return tenant


def _map(reload=False):
    global _by_slug

    if _by_slug is None or reload:
        _by_slug = {}

        for record in _records():
            tenant = _tenant(record)

            if tenant is None:
                continue

            for value in (record.get("subdomain"), record.get("key")):
                _by_slug.setdefault(slug(value), tenant)

        _by_slug.pop("", None)

    return _by_slug


def _tenant(record):
    uri = record.get("dbUri") or ""
    subdomain = (record.get("subdomain") or "").strip()

    try:
        name = parse_uri(uri)["database"]
    except Exception:
        name = None

    if not name or not subdomain:
        logger.warning(
            "Tenant %r has no %s; skipped.",
            record.get("name") or record.get("key"),
            "database in its dbUri" if not name else "subdomain",
        )
        return None

    return {
        "key": slug(record.get("key")) or slug(record.get("subdomain")),
        "name": record.get("name", ""),
        "subdomain": subdomain,
        "uri": uri,
        "db": name,
    }


def _records():
    global _client

    if _client is None:
        if not settings.CENTRAL_MONGODB_URI:
            raise TenantError(messages["centralUriMissing"])

        _client = MongoClient(
            settings.CENTRAL_MONGODB_URI, serverSelectionTimeoutMS=8000
        )

    try:
        return list(
            _client[settings.CENTRAL_MONGODB_DB][COLLECTION].find(ACTIVE)
        )
    except Exception as exc:
        raise TenantError(str(exc)) from exc