import json

from editorial_engine.fixtures import load_manifest
from editorial_engine.qc import check_claims, detect_generic_language, run_qc, verify_quotes


def test_generic_language_detector_reports_named_counts():
    result = detect_generic_language("Delve into the detail. It is important to note this. Delve into the data.")
    assert result["counts"]["DELVE_INTO"] == 2
    assert result["counts"]["IMPORTANT_TO_NOTE"] == 1
    assert result["total"] == 3


def test_generic_language_threshold_fails_with_counts(package):
    path = package / "style_seed.md"
    path.write_text("Delve into the report. [C001] Delve into the table. [C002]\n", encoding="utf-8")
    result = run_qc(package, slop_threshold=1)
    check = result["checks"]["GENERIC_AI_LANGUAGE"]
    assert not check["passed"]
    assert check["counts"]["DELVE_INTO"] == 2
    assert check["total"] == 2


def test_quote_verification_passes_verbatim_and_fails_invented(package):
    manifest = load_manifest(package / "source_fixtures")
    quotes_path = package / "quotes.json"
    quotes = json.loads(quotes_path.read_text(encoding="utf-8"))
    assert verify_quotes(quotes, manifest, package / "source_fixtures") == []
    quotes[0]["text"] = "An invented statement that the transcript never contains."
    quotes_path.write_text(json.dumps(quotes), encoding="utf-8")
    result = run_qc(package)
    failures = result["checks"]["QUOTE_VERIFICATION"]["failures"]
    assert not result["checks"]["QUOTE_VERIFICATION"]["passed"]
    assert failures[0]["expected"] == quotes[0]["text"]
    assert "QUOTABLE" in failures[0]["actual"]


def test_claim_with_missing_source_is_flagged(sources):
    manifest = load_manifest(sources)
    claim = {"claim_id": "C999", "text": "An unsourced statement.", "source_id": None, "locator": "", "evidence": []}
    issues = check_claims([claim], manifest, sources)
    assert issues[0]["reason"] == "missing_or_unknown_source"
