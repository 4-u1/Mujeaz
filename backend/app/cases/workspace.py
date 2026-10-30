"""Work queue and document viewer (M3).

The queue priority is a stated formula, shown to the user (decision D4):
    priority = amount × min(1 + 0.1 × days since request, 3)
where amount is the revenue at risk once analysed, or the full requested value before analysis.
"""

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import Connection, text

AGE_FACTOR_CAP = 3.0
FORMULA = "amount × min(1 + 0.1 × days since request, 3); amount = revenue at risk (or full value if not analysed)"
FORMULA_AR = "المبلغ × الأصغر من (1 + 0.1 × أيام منذ الطلب، 3)؛ المبلغ = الإيراد المعرض للخطر (أو القيمة كاملة قبل التحليل)"
ACTIVE = ("DRAFT", "RISK_DETECTED", "EVIDENCE_SEARCHING", "DECISION_READY")


def utf16_index(s: str, i: int) -> int:
    """Code-point offset → UTF-16 code-unit offset (what JavaScript strings index)."""
    return len(s[:i].encode("utf-16-le")) // 2


def _next_action(status: str, analyzed: bool, open_q: int, declined: int) -> tuple[str, str]:
    if not analyzed or status == "DRAFT":
        return "Analyze", "تحليل"
    if status == "DECISION_READY":
        return "Review and approve submission", "مراجعة واعتماد الإرسال"
    if open_q:
        return "Awaiting physician documentation", "بانتظار توثيق الطبيب"
    if declined:
        return "Physician declined: review the case", "اعتذر الطبيب: راجع الحالة"
    return "Review risk", "مراجعة المخاطر"


def queue(conn: Connection, *, today: date | None = None, limit: int = 100) -> list[dict[str, Any]]:
    today = today or datetime.now(UTC).date()
    rows = conn.execute(text(
        """
        SELECT ar.id, ar.case_number, ar.status, ar.requested_service, ar.requested_on, ar.financial_value_sar,
               p.code AS payer_code, rr.revenue_at_risk_sar, rr.denial_risk_pct, rs.overall_score,
               (SELECT count(*) FROM documentation_queries q WHERE q.authorization_request_id = ar.id
                  AND q.status = 'OPEN') AS open_queries,
               (SELECT count(*) FROM documentation_queries q WHERE q.authorization_request_id = ar.id
                  AND q.status = 'DECLINED') AS declined_queries
        FROM authorization_requests ar JOIN payers p ON p.id = ar.payer_id
        LEFT JOIN LATERAL (SELECT * FROM revenue_risk r WHERE r.authorization_request_id = ar.id
                           ORDER BY r.computed_at DESC LIMIT 1) rr ON true
        LEFT JOIN LATERAL (SELECT * FROM readiness_scores s WHERE s.authorization_request_id = ar.id
                           ORDER BY s.computed_at DESC LIMIT 1) rs ON true
        WHERE ar.status = ANY(:active)
        """), {"active": list(ACTIVE)}).mappings().all()
    items = []
    for r in rows:
        analyzed = r["overall_score"] is not None
        amount = float(r["revenue_at_risk_sar"] if analyzed else r["financial_value_sar"])
        days = max(0, (today - r["requested_on"]).days)
        factor = min(1 + 0.1 * days, AGE_FACTOR_CAP)
        action, action_ar = _next_action(r["status"], analyzed, r["open_queries"], r["declined_queries"])
        items.append({
            "id": str(r["id"]), "caseNumber": r["case_number"], "status": r["status"], "payerCode": r["payer_code"],
            "requestedService": r["requested_service"], "requestedOn": r["requested_on"].isoformat(),
            "analyzed": analyzed, "readiness": r["overall_score"], "denialRisk": r["denial_risk_pct"],
            "amount": round(amount), "amountBasis": "revenue_at_risk" if analyzed else "full_value",
            "daysSinceRequest": days, "ageFactor": round(factor, 2), "priority": round(amount * factor),
            "openQueries": r["open_queries"], "declinedQueries": r["declined_queries"],
            "nextAction": action, "nextActionAr": action_ar,
        })
    items.sort(key=lambda x: (-x["priority"], x["caseNumber"]))
    return items[:limit]


def documents(conn: Connection, case_id: str) -> dict[str, Any] | None:
    case = conn.execute(text("SELECT patient_id, requested_on FROM authorization_requests WHERE id = :c"),
                        {"c": case_id}).mappings().first()
    if case is None:
        return None
    docs = conn.execute(text(
        "SELECT id, doc_ref, doc_type, language, authored_on, content, signed_at FROM clinical_documents "
        "WHERE patient_id = :p AND ((authorization_request_id IS NULL AND authored_on <= :d) "
        "OR authorization_request_id = :c) ORDER BY (doc_type = 'addendum'), authored_on DESC, doc_ref"),
        {"p": case["patient_id"], "d": case["requested_on"], "c": case_id}).mappings().all()
    facts = conn.execute(text(
        "SELECT f.id, d.doc_ref, f.label, f.char_start, f.char_end FROM clinical_facts f "
        "JOIN clinical_documents d ON d.id = f.document_id WHERE f.authorization_request_id = :c "
        "AND f.label IS NOT NULL ORDER BY f.ord"), {"c": case_id}).mappings().all()
    run = conn.execute(text(
        "SELECT result->'evidence' AS evidence FROM analysis_runs WHERE authorization_request_id = :c "
        "AND status = 'COMPLETED' ORDER BY started_at DESC LIMIT 1"), {"c": case_id}).mappings().first()
    content = {d["doc_ref"]: d["content"] for d in docs}

    def span(ref: str, s: int, e: int) -> dict[str, Any]:
        t = content.get(ref, "")
        return {"docRef": ref, "start": s, "end": e, "utf16Start": utf16_index(t, s), "utf16End": utf16_index(t, e)}

    retrieved = {}
    for rid, ev in ((run or {}).get("evidence") or {}).items():
        retrieved[rid] = [{**span(ref, s, e), "score": score} for ref, s, e, score in ev.get("retrieved", [])
                          if ref in content]
    return {
        "documents": [{"docRef": d["doc_ref"], "docType": d["doc_type"], "language": d["language"],
                       "authoredOn": d["authored_on"].isoformat(), "content": d["content"],
                       "postRequestAddendum": d["doc_type"] == "addendum",
                       "signedAt": d["signed_at"].isoformat() if d["signed_at"] else None} for d in docs],
        "facts": [{"id": str(f["id"]), "label": f["label"], **span(f["doc_ref"], f["char_start"], f["char_end"])}
                  for f in facts],
        "retrieved": retrieved,
    }
