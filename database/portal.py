import json
from datetime import date

from bson import ObjectId
from pymongo import MongoClient

from utils.enums import CaptureType, Recency
from utils.messages import PortalError

COLLECTION = "onsiteenrollmentcaptures"
PRACTICES = "practices"
REMOTE = {"type": CaptureType.remote.value}

_clients = {}


def captures(tenant):
    uri = tenant["uri"]

    if uri not in _clients:
        _clients[uri] = MongoClient(uri, serverSelectionTimeoutMS=8000)

    return _clients[uri][tenant["db"]][COLLECTION]


def list_patients(tenant):
    try:
        found = captures(tenant).find(REMOTE).sort("capturedAt", -1)
        return [summary(capture) for capture in found]
    except Exception as exc:
        raise PortalError(str(exc)) from exc


def get_patient(tenant, patient_id):
    try:
        object_id = ObjectId(patient_id)
    except Exception:
        return None

    try:
        return captures(tenant).find_one({"_id": object_id, **REMOTE})
    except Exception as exc:
        raise PortalError(str(exc)) from exc


def practice_phone(tenant, capture):
    practice_id = capture.get("practiceId")

    if not practice_id:
        return ""

    try:
        found = captures(tenant).database[PRACTICES].find_one(
            {"_id": ObjectId(practice_id)}, {"phone": 1, "contactPhone": 1}
        )
    except Exception:
        return ""

    if not found:
        return ""

    return format_phone(found.get("phone") or found.get("contactPhone") or "")


def format_phone(number):
    digits = "".join(c for c in number if c.isdigit())

    if len(digits) != 10:
        return number.strip()

    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"


def full_name(capture):
    parts = [capture.get("firstName"), capture.get("lastName")]
    return " ".join(part for part in parts if part).strip()


def summary(capture):
    return {
        "patient_id": str(capture["_id"]),
        "name": full_name(capture),
        "practice": capture.get("practiceName", ""),
        "provider": capture.get("primaryProviderName", ""),
        "programs": capture.get("programs") or [],
        "latest_appointment_date": capture.get("latestAppointmentDate", ""),
    }


def recency(capture):
    seen = capture.get("latestAppointmentDate")

    if not seen:
        return Recency.year

    try:
        days = (date.today() - date.fromisoformat(seen[:10])).days
    except ValueError:
        return Recency.year

    return Recency.oneMonth if days <= 60 else Recency.year


def profile(capture):
    return json.dumps(capture, indent=2, default=str, ensure_ascii=False)