"""Read-only access to the practice portal's enrollment captures.

The portal lives on its own Mongo cluster, so it is read with pymongo
directly rather than through a Django model. Only remote captures are ever
visible here - onsite patients are enrolled at the desk, not by Emma.

A capture is a wide document. `profile` hands the whole of it to Emma, and
`summary` is the short version the portal lists patients by.
"""
import json
from datetime import date

from bson import ObjectId
from django.conf import settings
from pymongo import MongoClient

COLLECTION = "onsiteenrollmentcaptures"
REMOTE = {"type": "remote"}

_collection = None


class PortalError(Exception):
    """Raised when the portal cannot be reached or read."""


def captures():
    """The remote-captures collection, opened once and reused."""
    global _collection

    if _collection is None:
        if not settings.PORTAL_MONGODB_URI:
            raise PortalError("PORTAL_MONGODB_URI is not configured.")

        client = MongoClient(
            settings.PORTAL_MONGODB_URI, serverSelectionTimeoutMS=8000
        )
        _collection = client[settings.PORTAL_MONGODB_DB][COLLECTION]

    return _collection


def list_patients():
    """Every remote patient, newest capture first."""
    try:
        found = captures().find(REMOTE).sort("capturedAt", -1)
        return [summary(capture) for capture in found]
    except Exception as exc:
        raise PortalError(str(exc)) from exc


def get_patient(patient_id):
    """One remote patient by capture id, or None if there is no such patient."""
    try:
        object_id = ObjectId(patient_id)
    except Exception:
        return None

    try:
        return captures().find_one({"_id": object_id, **REMOTE})
    except Exception as exc:
        raise PortalError(str(exc)) from exc


def full_name(capture):
    parts = [capture.get("firstName"), capture.get("lastName")]
    return " ".join(part for part in parts if part).strip()


def summary(capture):
    """One patient, as the portal lists them."""
    return {
        "patient_id": str(capture["_id"]),
        "name": full_name(capture),
        "practice": capture.get("practiceName", ""),
        "provider": capture.get("primaryProviderName", ""),
        "programs": capture.get("programs") or [],
        "latest_appointment_date": capture.get("latestAppointmentDate", ""),
    }


def recency(capture):
    """How long ago the patient was seen, in the wording the opener expects."""
    seen = capture.get("latestAppointmentDate")

    if not seen:
        return "year"

    try:
        days = (date.today() - date.fromisoformat(seen[:10])).days
    except ValueError:
        return "year"

    # A future appointment means they are booked in, not overdue, so treat
    # them the same as a patient seen recently.
    return "onemonth" if days <= 60 else "year"


def profile(capture):
    """The patient's whole capture, as JSON the model can read.

    Everything on the record goes to Emma - nothing is picked out here, so a
    field the portal adds later reaches her without a code change. `default`
    turns the ObjectIds and dates into strings.
    """
    return json.dumps(capture, indent=2, default=str, ensure_ascii=False)
