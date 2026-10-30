"""Builds a PatientRecord from a synthetic FHIR R4 bundle (eval runner and seeder)."""

import base64
from datetime import date
from typing import Any

from app.agents.types import Document, PatientRecord


def documents_from_bundle(bundle: dict[str, Any]) -> tuple[Document, ...]:
    docs = []
    for e in bundle["entry"]:
        r = e["resource"]
        if r["resourceType"] != "DocumentReference":
            continue
        att = r["content"][0]["attachment"]
        docs.append(Document(r["id"], r["type"]["text"], att.get("language", "en"),
                             date.fromisoformat(r["date"][:10]), base64.b64decode(att["data"]).decode("utf-8")))
    return tuple(docs)


def record_from_bundle(bundle: dict[str, Any], *, payer_code: str = "DPA") -> PatientRecord:
    res = [e["resource"] for e in bundle["entry"]]
    dx = next(r for r in res if r["resourceType"] == "Condition")["code"]["coding"][0]["code"]
    sr = next(r for r in res if r["resourceType"] == "ServiceRequest")
    docs = documents_from_bundle(bundle)
    requested = sr.get("authoredOn") or (docs[0].authored_on.isoformat() if docs and docs[0].authored_on else None)
    return PatientRecord(bundle["id"], docs, dx, sr["code"]["coding"][0]["code"], payer_code,
                         date.fromisoformat(requested[:10]) if requested else None, docs[0].doc_ref if docs else None)
