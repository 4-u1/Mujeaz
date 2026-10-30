from app.agents.verify import locate
from app.nlp.chunker import chunk
from app.nlp.text import normalize, normalize_with_map, tokens


def test_arabic_normalisation_folds_variants_digits_and_diacritics() -> None:
    assert normalize("أكمل ٦ جلساتٍ") == "اكمل 6 جلسات"
    assert normalize("إحالة  —  مُستشفى") == "احاله - مستشفي"


def test_map_points_back_to_original_characters() -> None:
    src = "مُريض  ٦"
    norm, mapping = normalize_with_map(src)
    assert len(norm) == len(mapping)
    for i, c in enumerate(norm):
        if c.isdigit():
            assert src[mapping[i]] == "٦"


def test_tokens_stem_arabic_and_english() -> None:
    assert "جلس" in tokens("الجلسات") or "جلسات" in tokens("الجلسات")
    assert tokens("sessions completed") == ["session", "complet"]


def test_chunks_keep_exact_offsets() -> None:
    text = "Pain for 8 weeks. SLR positive at 45 degrees.\nPlan: MRI lumbar spine without contrast."
    cs = chunk(text)
    assert [c.text for c in cs][0] == "Pain for 8 weeks."
    for c in cs:
        assert text[c.start:c.end] == c.text
    assert "6.5" in chunk("Took 6.5 weeks of therapy.")[0].text


def test_arabic_question_mark_is_a_boundary() -> None:
    assert len(chunk("هل أكمل العلاج؟ نعم.")) == 2


def test_locate_exact_and_normalised() -> None:
    doc = "ملخص: أكمل ٦ جلسات علاج طبيعي على مدى ٧ أسابيع."
    exact = locate("٦ جلسات علاج طبيعي", doc)
    assert exact and exact.exact and doc[exact.start:exact.end] == "٦ جلسات علاج طبيعي"
    fuzzy = locate("اكمل 6 جلسات", doc)
    assert fuzzy and not fuzzy.exact and doc[fuzzy.start:fuzzy.end] == "أكمل ٦ جلسات"


def test_locate_rejects_invented_quotes() -> None:
    assert locate("completed 12 sessions of hydrotherapy", "Physiotherapy: 6 sessions over 7 weeks.") is None
    assert locate("ab", "abc") is None
