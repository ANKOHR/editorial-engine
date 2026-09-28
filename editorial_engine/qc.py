"""Named rule-based quality checks for claims, language, and quotes."""

import json
import re
from pathlib import Path

from .fixtures import document_index, load_manifest
from .pipeline import provenance_banner


SLOP_PATTERNS = {
    "FAST_PACED_WORLD": r"in (?:today's|the) fast-paced world",
    "DELVE_INTO": r"\bdelve into\b",
    "IMPORTANT_TO_NOTE": r"\bit is important to note\b",
    "UNLOCK_THE_POWER": r"\bunlock the power of\b",
    "GAME_CHANGER": r"\bgame[- ]changer\b",
    "SEAMLESSLY": r"\bseamlessly\b",
    "ROBUST_SOLUTION": r"\brobust solution\b",
    "IN_CONCLUSION": r"\bin conclusion\b",
    "LANDSCAPE_METAPHOR": r"\bin the (?:ever[- ]changing )?landscape of\b",
    "TAPESTRY_METAPHOR": r"\bweave(?:s|d)? a tapestry\b",
}


def detect_generic_language(text: str) -> dict:
    counts = {}
    matches = []
    for name, pattern in SLOP_PATTERNS.items():
        found = list(re.finditer(pattern, text, flags=re.IGNORECASE))
        counts[name] = len(found)
        matches.extend({"pattern": name, "text": match.group(0)} for match in found)
    return {"counts": counts, "total": sum(counts.values()), "matches": matches}


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def check_claims(claims: list[dict], manifest: dict, sources_dir: Path) -> list[dict]:
    """Return all claims whose source, locator, or evidence cannot be verified."""
    docs = document_index(manifest)
    issues = []
    for claim in claims:
        cid = claim.get("claim_id", "<missing-id>")
        source_id = claim.get("source_id")
        doc = docs.get(source_id)
        if not source_id or doc is None:
            issues.append({"claim_id": cid, "reason": "missing_or_unknown_source", "source_id": source_id, "text": claim.get("text", "")})
            continue
        source_path = Path(sources_dir) / doc["path"]
        raw = source_path.read_text(encoding="utf-8")
        locator = claim.get("locator", "")
        if not locator:
            issues.append({"claim_id": cid, "reason": "missing_locator", "source_id": source_id, "text": claim.get("text", "")})
        elif locator.startswith("rows:"):
            wanted_rows = locator.removeprefix("rows:").split(",")
            present = {line.split(",", 1)[0] for line in raw.splitlines()[1:] if line.strip()}
            if not all(row in present for row in wanted_rows):
                issues.append({"claim_id": cid, "reason": "invalid_locator", "source_id": source_id, "locator": locator, "text": claim.get("text", "")})
        elif locator not in raw:
            issues.append({"claim_id": cid, "reason": "invalid_locator", "source_id": source_id, "locator": locator, "text": claim.get("text", "")})
        evidence = claim.get("evidence", [])
        if isinstance(evidence, str):
            evidence = [evidence]
        if not evidence or any(item not in raw for item in evidence):
            issues.append({"claim_id": cid, "reason": "evidence_not_found", "source_id": source_id, "locator": locator, "text": claim.get("text", ""), "evidence": evidence})
    return issues


def verify_quotes(quotes: list[dict], manifest: dict, sources_dir: Path) -> list[dict]:
    docs = document_index(manifest)
    failures = []
    for quote in quotes:
        expected = quote.get("text", "")
        doc = docs.get(quote.get("source_id"))
        actual = "<source document not found>"
        if doc:
            source_path = Path(sources_dir) / doc["path"]
            if source_path.is_file():
                raw = source_path.read_text(encoding="utf-8")
                if expected and expected in raw:
                    continue
                line = quote.get("locator", "")
                actual = next((item for item in raw.splitlines() if line and line in item), "<quote text not found at expected source>")
        failures.append({"quote_id": quote.get("quote_id", "<missing-id>"), "source_id": quote.get("source_id"), "locator": quote.get("locator", ""), "expected": expected, "actual": actual})
    return failures


def _assembled_text(package_dir: Path) -> str:
    excluded = {"citations.md", "qc_report.md", "package.md"}
    pieces = []
    for path in sorted(Path(package_dir).glob("*.md")):
        if path.name not in excluded:
            pieces.append(path.read_text(encoding="utf-8"))
    return "\n".join(pieces)


def _unlinked_sentences(package_dir: Path) -> list[dict]:
    """Flag authored prose sentences with no inline claim or quote reference."""
    excluded = {"citations.md", "qc_report.md", "package.md"}
    issues = []
    for path in sorted(Path(package_dir).glob("*.md")):
        if path.name in excluded:
            continue
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith((">", "#")):
                continue
            if re.match(r"- (?:Chart type|Data mapping|Visual):", stripped, flags=re.IGNORECASE):
                continue
            # Move trailing references before punctuation so each sentence keeps its reference.
            normalized = re.sub(r"([.!?])\s*(\[(?:C|Q)\d{3}\])", r"\2\1", stripped)
            for sentence in re.split(r"(?<!\d)[.!?]\s+", normalized):
                sentence = sentence.strip()
                if sentence and not re.search(r"\[(?:C|Q)\d{3}\]", sentence):
                    issues.append({"path": path.name, "line": line_number, "reason": "sentence_has_no_source_marker", "text": sentence})
    return issues


def validate_citations(package_dir: Path) -> dict:
    package_dir = Path(package_dir)
    sources_dir = package_dir / "source_fixtures"
    manifest = load_manifest(sources_dir)
    claims = _load_json(package_dir / "claims.json")
    errors = check_claims(claims, manifest, sources_dir)
    errors.extend(_unlinked_sentences(package_dir))
    content = _assembled_text(package_dir)
    known = {claim.get("claim_id") for claim in claims}
    referenced = set(re.findall(r"\[(C\d{3})\]", content))
    for unknown in sorted(referenced - known):
        errors.append({"claim_id": unknown, "reason": "claim_marker_has_no_record"})
    for missing in sorted(known - referenced):
        errors.append({"claim_id": missing, "reason": "claim_not_used_in_assembled_copy"})
    for unknown in sorted(set(re.findall(r"\[(Q\d{3})\]", content)) - {q["quote_id"] for q in _load_json(package_dir / "quotes.json")}):
        errors.append({"claim_id": unknown, "reason": "quote_marker_has_no_record"})
    return {"passed": not errors, "claim_count": len(claims), "errors": errors, "claims": claims}


def write_citation_report(package_dir: Path) -> dict:
    package_dir = Path(package_dir)
    report = validate_citations(package_dir)
    manifest = load_manifest(package_dir / "source_fixtures")
    banner = provenance_banner(manifest)
    (package_dir / "claims_table.csv").write_text(
        "claim_id,text,source_id,locator,evidence,outputs\n" + "".join(
            ",".join('"' + str(value).replace('"', '""') + '"' for value in [c.get("claim_id", ""), c.get("text", ""), c.get("source_id", ""), c.get("locator", ""), " | ".join(c.get("evidence", [])), ";".join(c.get("outputs", []))]) + "\n"
            for c in report["claims"]
        ), encoding="utf-8", newline="\n")
    lines = [banner, "", "# Citation report", "", f"Status: {'PASS' if report['passed'] else 'FAIL'}", "", "Each claim record is checked against a synthetic fixture document, locator, and source evidence. Missing or invalid links are listed below.", "", "| Claim | Statement | Fixture source | Locator | Evidence |", "| --- | --- | --- | --- | --- |"]
    for claim in report["claims"]:
        evidence = "; ".join(claim.get("evidence", [])).replace("|", "\\|")
        lines.append(f"| {claim['claim_id']} | {claim['text']} | {claim['source_id']} | {claim['locator']} | `{evidence}` |")
    quotes = _load_json(package_dir / "quotes.json")
    lines.extend(["", "## Verbatim quote sources", "", "| Quote | Speaker | Fixture source | Locator | Exact text |", "| --- | --- | --- | --- | --- |"])
    for quote in quotes:
        exact_text = quote.get("text", "").replace("|", "\\|")
        lines.append(f"| {quote.get('quote_id', '')} | {quote.get('speaker', '')} | {quote.get('source_id', '')} | {quote.get('locator', '')} | {exact_text} |")
    lines.extend(["", "Quote verification searches the named transcript source for this full text verbatim.", "The CSV claims table is available as `claims_table.csv`."])
    if report["errors"]:
        lines.extend(["", "## Unlinked or invalid claims", ""])
        lines.extend(f"- {error.get('claim_id')}: {error.get('reason')}" for error in report["errors"])
    (package_dir / "citations.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return report


def run_qc(package_dir: Path, slop_threshold: int = 0) -> dict:
    package_dir = Path(package_dir)
    sources_dir = package_dir / "source_fixtures"
    manifest = load_manifest(sources_dir)
    citation_result = validate_citations(package_dir)
    quotes = _load_json(package_dir / "quotes.json")
    quote_failures = verify_quotes(quotes, manifest, sources_dir)
    language = detect_generic_language(_assembled_text(package_dir))
    failures = []
    if language["total"] > slop_threshold:
        failures.append({"check": "GENERIC_AI_LANGUAGE", "reason": "occurrences_above_threshold", "occurrences": language["total"], "threshold": slop_threshold})
    if citation_result["errors"]:
        failures.append({"check": "UNSUPPORTED_CLAIMS", "issues": citation_result["errors"]})
    if quote_failures:
        failures.append({"check": "QUOTE_VERIFICATION", "failures": quote_failures})
    report = {
        "passed": not failures,
        "synthetic": True,
        "sources": [doc["id"] for doc in manifest["documents"]],
        "threshold": slop_threshold,
        "checks": {
            "GENERIC_AI_LANGUAGE": {"passed": language["total"] <= slop_threshold, "catalogue": SLOP_PATTERNS, **language},
            "UNSUPPORTED_CLAIMS": {"passed": not citation_result["errors"], "issue_count": len(citation_result["errors"]), "issues": citation_result["errors"]},
            "QUOTE_VERIFICATION": {"passed": not quote_failures, "quote_count": len(quotes), "failures": quote_failures},
        },
        "failures": failures,
    }
    (package_dir / "qc_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    banner = provenance_banner(manifest)
    lines = [banner, "", "# QC report", "", f"Overall: {'PASS' if report['passed'] else 'FAIL'}", "", f"- GENERIC_AI_LANGUAGE: {'PASS' if report['checks']['GENERIC_AI_LANGUAGE']['passed'] else 'FAIL'}, {language['total']} occurrence(s), threshold {slop_threshold}.", f"- UNSUPPORTED_CLAIMS: {'PASS' if report['checks']['UNSUPPORTED_CLAIMS']['passed'] else 'FAIL'}, {len(citation_result['errors'])} issue(s).", f"- QUOTE_VERIFICATION: {'PASS' if report['checks']['QUOTE_VERIFICATION']['passed'] else 'FAIL'}, {len(quote_failures)} failure(s)."]
    for failure in quote_failures:
        lines.extend(["", f"Quote {failure['quote_id']} failed verbatim verification.", f"Expected: {failure['expected']}", f"Actual: {failure['actual']}"])
    (package_dir / "qc_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return report
