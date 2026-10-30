"""M3 work queue helpers and UTF-16 offsets."""

from app.cases.workspace import _next_action, utf16_index


def test_utf16_offsets_match_javascript_indexing() -> None:
    s = "ألم 🙂 physiotherapy 8 sessions"
    i = s.index("physio")
    assert utf16_index(s, i) == i + 1  # the emoji is two UTF-16 code units
    assert utf16_index("علاج طبيعي", 4) == 4  # Arabic is in the BMP
    assert utf16_index(s, 0) == 0


def test_next_action() -> None:
    assert _next_action("DRAFT", False, 0, 0)[0] == "Analyze"
    assert _next_action("RISK_DETECTED", True, 1, 0)[0] == "Awaiting physician documentation"
    assert _next_action("RISK_DETECTED", True, 0, 1)[0].startswith("Physician declined")
    assert _next_action("DECISION_READY", True, 0, 0)[0] == "Review and approve submission"
