"""Deterministic editorial package assembly and source provenance."""

import csv
import html
import json
import shutil
from pathlib import Path

from . import DEFAULT_SEED
from .fixtures import load_manifest


def provenance_banner(manifest: dict) -> str:
    names = ", ".join(doc["id"] for doc in manifest["documents"])
    return (
        f"> Provenance: all content on this page derives from these synthetic fixture sources: {names}. "
        "All sources and figures are fictional. Deterministic assembly, rules-based QC, no generative model, no real publications cited."
    )


def _write_md(path: Path, banner: str, content: str) -> None:
    path.write_text(f"{banner}\n\n{content.rstrip()}\n", encoding="utf-8", newline="\n")


def _claim(cid: str, text: str, source_id: str, locator: str, evidence: list[str], outputs: list[str]) -> dict:
    return {
        "claim_id": cid,
        "text": text,
        "source_id": source_id,
        "locator": locator,
        "evidence": evidence,
        "outputs": outputs,
    }


def _fixture_corpus(src_dir: Path) -> tuple[list[dict], list[dict]]:
    manifest = load_manifest(src_dir)
    docs = {d["id"]: d for d in manifest["documents"]}
    dataset_path = src_dir / docs["DATA-001"]["path"]
    with dataset_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(line for line in handle if not line.startswith("#")))
    baseline = next(row for row in rows if row["period"] == "baseline")
    week4 = next(row for row in rows if row["period"] == "week_4")
    week8 = next(row for row in rows if row["period"] == "week_8")
    data_evidence = [
        ",".join(["baseline", baseline["focus_hours"], baseline["interruptions"], baseline["participation_pct"]]),
        ",".join(["week_8", week8["focus_hours"], week8["interruptions"], week8["participation_pct"]]),
    ]
    claims = [
        _claim("C001", f"Average focused time was {baseline['focus_hours']} hours per week at baseline and {week8['focus_hours']} hours at week eight.", "DATA-001", "rows:baseline,week_8", data_evidence, ["article.md", "executive_summary.md", "social_posts.md", "newsletter.md", "infographic_concepts.md"]),
        _claim("C002", f"Average reported interruptions were {baseline['interruptions']} per week at baseline and {week8['interruptions']} per week at week eight.", "DATA-001", "rows:baseline,week_8", data_evidence, ["article.md", "executive_summary.md", "social_posts.md", "newsletter.md", "infographic_concepts.md"]),
        _claim("C003", f"Participation was {baseline['participation_pct']} percent at baseline and {week8['participation_pct']} percent at week eight.", "DATA-001", "rows:baseline,week_8", data_evidence, ["executive_summary.md", "social_posts.md", "newsletter.md"]),
        _claim("C004", "The fictional internal pilot included three teams.", "MEMO-001", "Pilot scope", ["The fictional internal pilot included three teams."], ["article.md", "newsletter.md"]),
        _claim("C005", "The pilot was not designed to establish that weekly planning caused the observed changes.", "MEMO-001", "Limitations", ["The pilot was not designed to establish that weekly planning caused the observed changes."], ["article.md", "executive_summary.md", "newsletter.md", "social_posts.md"]),
        _claim("C006", "The fictional research paper followed 48 volunteers on 12 fictional teams for eight weeks.", "PAPER-001", "Methods", ["The fictional pilot followed 48 volunteers on 12 fictional teams for 8 weeks."], ["article.md"]),
        _claim("C007", f"At week four, average focused time was {week4['focus_hours']} hours per week and reported interruptions averaged {week4['interruptions']} per week.", "DATA-001", "rows:week_4", [",".join(["week_4", week4["focus_hours"], week4["interruptions"], week4["participation_pct"]])], ["article.md"]),
        _claim("C008", f"Participation was {week4['participation_pct']} percent at week four.", "DATA-001", "rows:week_4", [",".join(["week_4", week4["focus_hours"], week4["interruptions"], week4["participation_pct"]])], ["article.md"]),
        _claim("C009", "Participants recorded focused work hours and interruptions each week.", "PAPER-001", "Methods", ["Participants recorded focused work hours and interruptions each week."], ["article.md"]),
        _claim("C010", "The dataset has period, focus_hours, interruptions, and participation_pct columns with baseline, week_4, and week_8 records.", "DATA-001", "rows:baseline,week_4,week_8", ["period,focus_hours,interruptions,participation_pct", *data_evidence[:1], ",".join(["week_4", week4["focus_hours"], week4["interruptions"], week4["participation_pct"]]), data_evidence[-1]], ["article.md"]),
    ]
    quotes = [
        {"quote_id": "Q001", "speaker": "Leah Chen", "text": "The weekly plan gave us a shared place to park urgent work.", "source_id": "INTERVIEW-001", "locator": "Line 2", "outputs": ["article.md", "social_posts.md", "newsletter.md"]},
        {"quote_id": "Q002", "speaker": "Omar Ruiz", "text": "We spent less time asking who owned the next step.", "source_id": "INTERVIEW-002", "locator": "Line 2", "outputs": ["social_posts.md", "newsletter.md"]},
    ]
    return claims, quotes


def _svg_chart(title: str, values: list[tuple[str, float]], unit: str, output: Path) -> None:
    width, height = 720, 420
    left, top, bottom = 82, 72, 340
    max_value = max(value for _, value in values) * 1.18
    bar_width = 105
    gap = 100
    items = []
    items.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">')
    items.append(f'<title>{html.escape(title)}</title>')
    items.append('<rect width="100%" height="100%" fill="#fbfaf7"/>')
    items.append(f'<text x="{left}" y="38" font-family="Arial,sans-serif" font-size="22" font-weight="700" fill="#182b36">{html.escape(title)}</text>')
    items.append(f'<text x="{left}" y="58" font-family="Arial,sans-serif" font-size="12" fill="#52616b">Fictional synthetic fixture data, {html.escape(unit)}</text>')
    items.append(f'<line x1="{left}" y1="{bottom}" x2="{width-28}" y2="{bottom}" stroke="#50616b" stroke-width="2"/>')
    for index, (label, value) in enumerate(values):
        x = left + 52 + index * (bar_width + gap)
        bar_height = (value / max_value) * (bottom - top)
        y = bottom - bar_height
        items.append(f'<rect x="{x}" y="{y:.2f}" width="{bar_width}" height="{bar_height:.2f}" rx="5" fill="#327c78"/>')
        items.append(f'<text x="{x + bar_width/2}" y="{y-10:.2f}" text-anchor="middle" font-family="Arial,sans-serif" font-size="15" fill="#182b36">{value:g}</text>')
        items.append(f'<text x="{x + bar_width/2}" y="{bottom+25}" text-anchor="middle" font-family="Arial,sans-serif" font-size="14" fill="#182b36">{html.escape(label)}</text>')
    items.append(f'<text x="{left}" y="{height-20}" font-family="Arial,sans-serif" font-size="11" fill="#52616b">Source: DATA-001 pilot_metrics.csv. Synthetic fixture only.</text>')
    items.append('</svg>')
    output.write_text("\n".join(items) + "\n", encoding="utf-8", newline="\n")


def _svg_line_chart(title: str, values: list[tuple[str, float]], unit: str, output: Path) -> None:
    width, height = 720, 420
    left, right, top, bottom = 82, 38, 78, 340
    maximum = max(value for _, value in values) * 1.18
    step = (width - left - right) / max(1, len(values) - 1)
    points = []
    items = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<title>{html.escape(title)}</title>',
        '<rect width="100%" height="100%" fill="#fbfaf7"/>',
        f'<text x="{left}" y="38" font-family="Arial,sans-serif" font-size="22" font-weight="700" fill="#182b36">{html.escape(title)}</text>',
        f'<text x="{left}" y="58" font-family="Arial,sans-serif" font-size="12" fill="#52616b">Fictional synthetic fixture data, {html.escape(unit)}</text>',
        f'<line x1="{left}" y1="{bottom}" x2="{width-right}" y2="{bottom}" stroke="#50616b" stroke-width="2"/>',
    ]
    for index, (label, value) in enumerate(values):
        x = left + index * step
        y = bottom - (value / maximum) * (bottom - top)
        points.append(f"{x:.2f},{y:.2f}")
        items.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="7" fill="#327c78"/>')
        items.append(f'<text x="{x:.2f}" y="{y-13:.2f}" text-anchor="middle" font-family="Arial,sans-serif" font-size="15" fill="#182b36">{value:g}</text>')
        items.append(f'<text x="{x:.2f}" y="{bottom+25}" text-anchor="middle" font-family="Arial,sans-serif" font-size="14" fill="#182b36">{html.escape(label)}</text>')
    items.insert(6, f'<polyline points="{" ".join(points)}" fill="none" stroke="#327c78" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>')
    items.append(f'<text x="{left}" y="{height-20}" font-family="Arial,sans-serif" font-size="11" fill="#52616b">Source: DATA-001 pilot_metrics.csv. Synthetic fixture only.</text>')
    items.append('</svg>')
    output.write_text("\n".join(items) + "\n", encoding="utf-8", newline="\n")


def assemble_package(sources_dir: Path, package_dir: Path, seed: int | None = None) -> dict:
    """Build all copy and visuals using fixed templates and fixture values."""
    sources_dir, package_dir = Path(sources_dir), Path(package_dir)
    manifest = load_manifest(sources_dir)
    actual_seed = manifest.get("seed", DEFAULT_SEED) if seed is None else seed
    claims, quotes = _fixture_corpus(sources_dir)
    package_dir.mkdir(parents=True, exist_ok=True)
    fixture_copy = package_dir / "source_fixtures"
    fixture_copy.mkdir(exist_ok=True)
    for doc in manifest["documents"]:
        destination = fixture_copy / doc["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(sources_dir / doc["path"], destination)
    shutil.copyfile(sources_dir / "fixture_manifest.json", fixture_copy / "fixture_manifest.json")
    banner = provenance_banner(manifest)

    article = """# A week, written down

## What the source set records

The fictional research paper followed 48 volunteers on 12 fictional teams for eight weeks. [C006] Participants recorded focused work hours and interruptions each week. [C009]

The planted dataset has period, focus_hours, interruptions, and participation_pct columns, with records for baseline, week four, and week eight. [C010] Each row gives the same measures for a different point in the synthetic series. [C010]

## Three points in the series

At baseline, average focused time was 12.4 hours per week and reported interruptions averaged 9.2 per week. [C001] Participation was 72 percent. [C003]

At week four, average focused time was 13.2 hours per week and reported interruptions averaged 8.4 per week. [C007] Participation was 83 percent. [C008]

At week eight, average focused time was 14.1 hours per week and reported interruptions averaged 7.8 per week. [C001] Participation was 91 percent. [C003]

Read side by side, the period rows show how a middle observation can add detail to a baseline and week-eight comparison. [C007] The SVG concepts use the same named dataset columns so readers can inspect the figures in chart form. [C010]

## Voices from the fictional interviews

Leah Chen, identified in her transcript as a fictional operations lead, described the planning routine this way: “The weekly plan gave us a shared place to park urgent work.” [Q001]

Omar Ruiz, identified as a fictional research coordinator, offered a second view of the routine: “We spent less time asking who owned the next step.” [Q002]

The quotes remain attributed to their transcript sources, while the figures remain attributed to the dataset. [Q001] [C001]

## Keep the boundary visible

The internal memo describes a separate fictional pilot that included three teams. [C004] It also states that this pilot was not designed to establish that weekly planning caused its observed changes. [C005]

These sources supply a checkable editorial exercise: synthetic rows for charts, fictional voices for attributed quotations, and an explicit limit in the memo. [C010] [Q001] [C005]
"""
    summary = """# Executive summary

- Average focused time was 12.4 hours per week at baseline and 14.1 hours at week eight. [C001]
- Average reported interruptions were 9.2 per week at baseline and 7.8 per week at week eight. [C002]
- Participation was 72 percent at baseline and 91 percent at week eight. [C003]
- The pilot was not designed to establish that weekly planning caused the observed changes. [C005]
"""
    social = """# Social posts

## Punchy

Three fictional teams took part in the internal pilot. [C004] Participation was 72 percent at baseline and 91 percent at week eight. [C003]

## Data-led

Average focused time was 12.4 hours per week at baseline and 14.1 hours at week eight. [C001] Average reported interruptions were 9.2 per week at baseline and 7.8 per week at week eight. [C002]

## Quote-led

“We spent less time asking who owned the next step.” Omar Ruiz, fictional research coordinator. [Q002] The pilot was not designed to establish that weekly planning caused the observed changes. [C005]
"""
    newsletter = """# The Editorial Engine demo newsletter

## This week's fictional pilot

Average focused time was 12.4 hours per week at baseline and 14.1 hours at week eight. [C001] Average reported interruptions were 9.2 per week at baseline and 7.8 per week at week eight. [C002] Participation was 72 percent at baseline and 91 percent at week eight. [C003]

The fictional internal pilot included three teams. [C004] Leah Chen said: “The weekly plan gave us a shared place to park urgent work.” [Q001] Omar Ruiz said: “We spent less time asking who owned the next step.” [Q002]

The pilot was not designed to establish that weekly planning caused the observed changes. [C005]
"""
    for name, content in [("article.md", article), ("executive_summary.md", summary), ("social_posts.md", social), ("newsletter.md", newsletter)]:
        _write_md(package_dir / name, banner, content)

    focus_values = [("baseline", 12.4), ("week 4", 13.2), ("week 8", 14.1)]
    interruption_values = [("baseline", 9.2), ("week 4", 8.4), ("week 8", 7.8)]
    data_path = fixture_copy / "pilot_metrics.csv"
    with data_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(line for line in handle if not line.startswith("#")))
    focus_values = [(row["period"].replace("_", " "), float(row["focus_hours"])) for row in rows]
    interruption_values = [(row["period"].replace("_", " "), float(row["interruptions"])) for row in rows]
    replacements = {
        "12.4": rows[0]["focus_hours"], "14.1": rows[-1]["focus_hours"],
        "13.2": rows[1]["focus_hours"],
        "9.2": rows[0]["interruptions"], "7.8": rows[-1]["interruptions"],
        "8.4": rows[1]["interruptions"],
        "72": rows[0]["participation_pct"], "91": rows[-1]["participation_pct"],
        "83": rows[1]["participation_pct"],
    }
    for name in ("executive_summary.md", "social_posts.md", "newsletter.md"):
        path = package_dir / name
        content = path.read_text(encoding="utf-8")
        for old, new in replacements.items():
            content = content.replace(old, new)
        path.write_text(content, encoding="utf-8", newline="\n")
    visuals = package_dir / "visuals"
    visuals.mkdir(exist_ok=True)
    _svg_chart("Average focused hours", focus_values, "hours per week", visuals / "focus_hours.svg")
    _svg_line_chart("Average reported interruptions", interruption_values, "interruptions per week", visuals / "interruptions.svg")
    concepts = """# Infographic concepts

## Focused hours, baseline to week eight

- Chart type: line chart with one point per dataset period.
- Data mapping: period on the horizontal axis, focus_hours on the vertical axis.
- Caption: Average focused time was 12.4 hours per week at baseline and 14.1 hours at week eight. [C001]
- Visual: ![Focused hours, fictional fixture data](visuals/focus_hours.svg)

## Reported interruptions, baseline to week eight

- Chart type: vertical bar chart with one bar per dataset period.
- Data mapping: period on the horizontal axis, interruptions on the vertical axis.
- Caption: Average reported interruptions were 9.2 per week at baseline and 7.8 per week at week eight. [C002]
- Visual: ![Interruptions, fictional fixture data](visuals/interruptions.svg)

All plotted values come from the fictional `pilot_metrics.csv` fixture. [C001] [C002]
"""
    _write_md(package_dir / "infographic_concepts.md", banner, concepts)

    concepts_path = package_dir / "infographic_concepts.md"
    concepts_text = concepts_path.read_text(encoding="utf-8")
    for old, new in replacements.items():
        concepts_text = concepts_text.replace(old, new)
    concepts_path.write_text(concepts_text, encoding="utf-8", newline="\n")

    # The article template mirrors values from the table instead of fixed text.
    article_path = package_dir / "article.md"
    article_text = article_path.read_text(encoding="utf-8")
    for old, new in replacements.items():
        article_text = article_text.replace(old, new)
    article_path.write_text(article_text, encoding="utf-8", newline="\n")

    (package_dir / "claims.json").write_text(json.dumps(claims, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    (package_dir / "quotes.json").write_text(json.dumps(quotes, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    metadata = {"seed": actual_seed, "sources": [doc["id"] for doc in manifest["documents"]], "synthetic": True, "assembly": "deterministic templates and rules"}
    (package_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return {"claims": claims, "quotes": quotes, "seed": actual_seed, "sources": metadata["sources"]}
