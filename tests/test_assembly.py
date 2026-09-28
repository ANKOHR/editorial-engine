import csv
import json

from editorial_engine.pipeline import assemble_package
from editorial_engine.qc import run_qc, write_citation_report


def test_assembly_uses_dataset_values_and_verbatim_quotes(package):
    article = (package / "article.md").read_text(encoding="utf-8")
    summary = (package / "executive_summary.md").read_text(encoding="utf-8")
    with (package / "source_fixtures" / "pilot_metrics.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(line for line in handle if not line.startswith("#")))
    assert f"At baseline, average focused time was {rows[0]['focus_hours']} hours per week" in article
    assert f"{rows[-1]['focus_hours']} hours at week eight" in summary
    assert len(article.split()) >= 200
    assert f"{rows[0]['participation_pct']} percent at baseline" in summary
    assert "The weekly plan gave us a shared place to park urgent work." in article
    assert "INTERVIEW-001" in article
    assert (package / "visuals" / "focus_hours.svg").is_file()
    assert "polyline" in (package / "visuals" / "interruptions.svg").read_text(encoding="utf-8")


def test_assembly_output_is_byte_identical_for_same_sources(tmp_path, sources):
    one, two = tmp_path / "one", tmp_path / "two"
    assemble_package(sources, one)
    assemble_package(sources, two)
    for directory in (one, two):
        write_citation_report(directory)
        assert run_qc(directory)["passed"]
    files_one = {p.relative_to(one).as_posix(): p.read_bytes() for p in one.rglob("*") if p.is_file()}
    files_two = {p.relative_to(two).as_posix(): p.read_bytes() for p in two.rglob("*") if p.is_file()}
    assert files_one == files_two


def test_citation_report_links_every_claim(package):
    report = write_citation_report(package)
    assert report["passed"]
    assert report["claim_count"] == 10
    assert "| C001 |" in (package / "citations.md").read_text(encoding="utf-8")
    assert (package / "claims_table.csv").is_file()


def test_unlinked_sentences_are_flagged(package):
    article = package / "article.md"
    article.write_text(article.read_text(encoding="utf-8") + "\nThis figure proves the method works.\n", encoding="utf-8")
    citation_report = write_citation_report(package)
    assert not citation_report["passed"]
    assert any(issue["reason"] == "sentence_has_no_source_marker" and "proves" in issue["text"] for issue in citation_report["errors"])
    qc = run_qc(package)
    assert not qc["checks"]["UNSUPPORTED_CLAIMS"]["passed"]


def test_dynamic_claim_registry_is_present(package):
    claims = json.loads((package / "claims.json").read_text(encoding="utf-8"))
    assert all(claim["source_id"] and claim["locator"] and claim["evidence"] for claim in claims)
