"""Generate fully synthetic fixture documents without external downloads."""

import csv
import json
from pathlib import Path

from . import DEFAULT_SEED


FIXTURE_FILES = {
    "PAPER-001": "research_paper.md",
    "INTERVIEW-001": "interview_leah.txt",
    "INTERVIEW-002": "interview_omar.txt",
    "MEMO-001": "internal_memo.md",
    "DATA-001": "pilot_metrics.csv",
}


def generate_fixtures(out_dir: Path, seed: int = DEFAULT_SEED) -> list[str]:
    """Write deterministic fictional sources and return their relative paths."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    fictional_period = 8
    paper = f"""# Synthetic Research Paper: Weekly Planning and Focus Time

SYNTHETIC FIXTURE. Fictional research paper created by Editorial Engine. It is not a real publication.

## Methods

The fictional pilot followed 48 volunteers on 12 fictional teams for {fictional_period} weeks. Participants recorded focused work hours and interruptions each week.

## Results

The synthetic study recorded average focused time of 12.4 hours per week at baseline and 14.1 hours per week at week eight.

Average reported interruptions changed from 9.2 per week at baseline to 7.8 per week at week eight.

## Statistics table

| period | focus_hours | interruptions | participation_pct |
| baseline | 12.4 | 9.2 | 72 |
| week_4 | 13.2 | 8.4 | 83 |
| week_8 | 14.1 | 7.8 | 91 |

These invented figures are planted for checking. They do not describe real people, organizations, or research.
"""
    interview_leah = """SYNTHETIC FIXTURE. Fictional interview transcript created by Editorial Engine.
Interviewee: Leah Chen, fictional operations lead
Interviewer: Fictional Editorial Engine demo interviewer

Line 1: We started putting the week plan in one shared place.
Line 2 [QUOTABLE]: The weekly plan gave us a shared place to park urgent work.
Line 3: That made it easier to talk about what had changed.
"""
    interview_omar = """SYNTHETIC FIXTURE. Fictional interview transcript created by Editorial Engine.
Interviewee: Omar Ruiz, fictional research coordinator
Interviewer: Fictional Editorial Engine demo interviewer

Line 1: The handoff list was visible to the whole pilot group.
Line 2 [QUOTABLE]: We spent less time asking who owned the next step.
Line 3: I would describe that as my experience, not a measured outcome.
"""
    memo = """# Internal Pilot Memo

SYNTHETIC FIXTURE. Fictional internal memo created by Editorial Engine.

## Pilot scope

The fictional internal pilot included three teams.

## Measurement note

Survey completion reached 91 percent at week eight.

## Limitations

The pilot was not designed to establish that weekly planning caused the observed changes.
"""
    (out_dir / "research_paper.md").write_text(paper, encoding="utf-8", newline="\n")
    (out_dir / "interview_leah.txt").write_text(interview_leah, encoding="utf-8", newline="\n")
    (out_dir / "interview_omar.txt").write_text(interview_omar, encoding="utf-8", newline="\n")
    (out_dir / "internal_memo.md").write_text(memo, encoding="utf-8", newline="\n")
    with (out_dir / "pilot_metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        handle.write("# SYNTHETIC FIXTURE. Fictional planted figures created by Editorial Engine.\n")
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["period", "focus_hours", "interruptions", "participation_pct"])
        writer.writerows([
            ["baseline", "12.4", "9.2", "72"],
            ["week_4", "13.2", "8.4", "83"],
            ["week_8", "14.1", "7.8", "91"],
        ])
    manifest = {
        "synthetic": True,
        "label": "All documents are fictional synthetic fixtures generated locally.",
        "seed": seed,
        "documents": [
            {"id": "PAPER-001", "path": "research_paper.md", "kind": "research_paper", "title": "Synthetic Research Paper: Weekly Planning and Focus Time"},
            {"id": "INTERVIEW-001", "path": "interview_leah.txt", "kind": "interview_transcript", "title": "Fictional interview with Leah Chen"},
            {"id": "INTERVIEW-002", "path": "interview_omar.txt", "kind": "interview_transcript", "title": "Fictional interview with Omar Ruiz"},
            {"id": "MEMO-001", "path": "internal_memo.md", "kind": "internal_memo", "title": "Fictional internal pilot memo"},
            {"id": "DATA-001", "path": "pilot_metrics.csv", "kind": "dataset", "title": "Fictional pilot metrics"},
        ],
    }
    (out_dir / "fixture_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return ["fixture_manifest.json", *FIXTURE_FILES.values()]


def load_manifest(sources_dir: Path) -> dict:
    sources_dir = Path(sources_dir)
    manifest_path = sources_dir / "fixture_manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"Missing fixture manifest: {manifest_path}")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if data.get("synthetic") is not True:
        raise ValueError("Source manifest is not labelled synthetic")
    docs = data.get("documents", [])
    if {doc.get("id") for doc in docs} != set(FIXTURE_FILES) or len(docs) != len(FIXTURE_FILES):
        raise ValueError("Source manifest must list exactly the generated synthetic fixture documents")
    for doc in data.get("documents", []):
        if FIXTURE_FILES.get(doc.get("id")) != doc.get("path"):
            raise ValueError(f"Unexpected fixture path for source {doc.get('id')}")
        path = sources_dir / doc["path"]
        if not path.is_file():
            raise ValueError(f"Fixture document {doc['id']} is missing: {doc['path']}")
        raw = path.read_text(encoding="utf-8")
        if "SYNTHETIC FIXTURE" not in raw:
            raise ValueError(f"Fixture label missing from {doc['path']}")
    return data


def document_index(manifest: dict) -> dict[str, dict]:
    return {doc["id"]: doc for doc in manifest["documents"]}
