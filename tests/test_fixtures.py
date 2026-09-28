import csv

from editorial_engine.fixtures import generate_fixtures, load_manifest


def _bytes_by_name(directory):
    return {path.relative_to(directory).as_posix(): path.read_bytes() for path in directory.rglob("*") if path.is_file()}


def test_fixture_generation_is_byte_deterministic(tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    generate_fixtures(first, seed=17)
    generate_fixtures(second, seed=17)
    assert _bytes_by_name(first) == _bytes_by_name(second)


def test_planted_fixture_documents_and_dataset(sources):
    manifest = load_manifest(sources)
    assert manifest["synthetic"] is True
    assert len(manifest["documents"]) == 5
    for document in manifest["documents"]:
        assert "SYNTHETIC FIXTURE" in (sources / document["path"]).read_text(encoding="utf-8")
    paper = (sources / "research_paper.md").read_text(encoding="utf-8")
    assert "12.4 hours per week at baseline and 14.1 hours per week at week eight" in paper
    assert "9.2 per week at baseline to 7.8 per week at week eight" in paper
    with (sources / "pilot_metrics.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(line for line in handle if not line.startswith("#")))
    assert list(rows[0]) == ["period", "focus_hours", "interruptions", "participation_pct"]
    assert rows[-1] == {"period": "week_8", "focus_hours": "14.1", "interruptions": "7.8", "participation_pct": "91"}


def test_interview_quotes_are_marked_quotable_and_verbatim(sources):
    leah = (sources / "interview_leah.txt").read_text(encoding="utf-8")
    omar = (sources / "interview_omar.txt").read_text(encoding="utf-8")
    assert "Line 2 [QUOTABLE]: The weekly plan gave us a shared place to park urgent work." in leah
    assert "Line 2 [QUOTABLE]: We spent less time asking who owned the next step." in omar
