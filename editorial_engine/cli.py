"""Command line interface and append-only local audit trail."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import DEFAULT_SEED, __version__
from .fixtures import generate_fixtures, load_manifest
from .pipeline import assemble_package, provenance_banner
from .qc import run_qc, write_citation_report
from .rendering import render_package


BOUNDARY = "Editorial Engine: synthetic sources, deterministic assembly, rules-based QC, no generative model, no real publications cited."
AUDIT_PATH = Path(__file__).resolve().parent.parent / "ee-audit.jsonl"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ee", description="Assemble deterministic editorial packages from fictional synthetic fixtures.", epilog=BOUNDARY)
    parser.add_argument("--version", action="version", version=f"ee {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    fixtures = commands.add_parser("fixtures", help="generate synthetic source fixtures")
    fixtures.add_argument("--out", required=True, type=Path)
    fixtures.add_argument("--seed", type=int, default=DEFAULT_SEED)
    assemble = commands.add_parser("assemble", help="assemble copy, infographic visuals, citations, and QC reports")
    assemble.add_argument("--sources", required=True, type=Path)
    assemble.add_argument("--out", type=Path, default=Path("editorial-package"))
    assemble.add_argument("--seed", type=int)
    citations = commands.add_parser("citations", help="validate claim links and write a citation report")
    citations.add_argument("package_dir", type=Path)
    qc = commands.add_parser("qc", help="run the named rules-based QC checks")
    qc.add_argument("package_dir", type=Path)
    qc.add_argument("--slop-threshold", type=int, default=0)
    package = commands.add_parser("package", help="render all package pages as Markdown or HTML")
    package.add_argument("package_dir", type=Path)
    package.add_argument("--format", required=True, choices=["md", "html"])
    return parser


def _append_audit(command: str, sources: list[str], outputs: list[str], qc_results: dict | None, seed: int) -> None:
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "subcommand": command,
        "sources": sources,
        "outputs": outputs,
        "qc_results": qc_results,
        "seed": seed,
    }
    with AUDIT_PATH.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def _package_outputs(package_dir: Path) -> list[str]:
    names = [
        "article.md", "executive_summary.md", "social_posts.md", "newsletter.md",
        "infographic_concepts.md", "claims.json", "quotes.json", "run_metadata.json",
        "claims_table.csv", "citations.md", "qc_report.json", "qc_report.md",
        "source_fixtures/fixture_manifest.json", "source_fixtures/research_paper.md",
        "source_fixtures/interview_leah.txt", "source_fixtures/interview_omar.txt",
        "source_fixtures/internal_memo.md", "source_fixtures/pilot_metrics.csv",
        "visuals/focus_hours.svg", "visuals/interruptions.svg",
    ]
    return [str(package_dir / name) for name in names if (package_dir / name).is_file()]


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    print(BOUNDARY)
    try:
        if args.command == "fixtures":
            outputs = generate_fixtures(args.out, args.seed)
            _append_audit("fixtures", [str(args.out)], [str(args.out / name) for name in outputs], None, args.seed)
            print(f"Generated {len(outputs) - 1} synthetic fixture documents in {args.out} with seed {args.seed}.")
            return 0
        if args.command == "assemble":
            result = assemble_package(args.sources, args.out, args.seed)
            citation_result = write_citation_report(args.out)
            qc_result = run_qc(args.out)
            _append_audit("assemble", [str(args.sources)], _package_outputs(args.out), qc_result, result["seed"])
            print(f"Assembled package at {args.out}. Citations: {'PASS' if citation_result['passed'] else 'FAIL'}. QC: {'PASS' if qc_result['passed'] else 'FAIL'}.")
            return 0 if qc_result["passed"] else 2
        if args.command == "citations":
            result = write_citation_report(args.package_dir)
            metadata = json.loads((args.package_dir / "run_metadata.json").read_text(encoding="utf-8"))
            _append_audit("citations", [str(args.package_dir / "source_fixtures")], [str(args.package_dir / "citations.md"), str(args.package_dir / "claims_table.csv")], {"passed": result["passed"], "issue_count": len(result["errors"])}, metadata["seed"])
            print(f"Citation report: {'PASS' if result['passed'] else 'FAIL'}, {result['claim_count']} claims checked, {len(result['errors'])} issue(s).")
            return 0 if result["passed"] else 2
        if args.command == "qc":
            if args.slop_threshold < 0:
                raise ValueError("slop threshold must be zero or greater")
            result = run_qc(args.package_dir, args.slop_threshold)
            metadata = json.loads((args.package_dir / "run_metadata.json").read_text(encoding="utf-8"))
            _append_audit("qc", [str(args.package_dir / "source_fixtures")], [str(args.package_dir / "qc_report.json"), str(args.package_dir / "qc_report.md")], result, metadata["seed"])
            for name, check in result["checks"].items():
                print(f"{name}: {'PASS' if check['passed'] else 'FAIL'}")
            return 0 if result["passed"] else 2
        if args.command == "package":
            qc_path = args.package_dir / "qc_report.json"
            if not qc_path.is_file():
                raise ValueError("Run ee assemble or ee qc before rendering the package")
            qc_result = json.loads(qc_path.read_text(encoding="utf-8"))
            manifest = load_manifest(args.package_dir / "source_fixtures")
            output = render_package(args.package_dir, args.format)
            metadata = json.loads((args.package_dir / "run_metadata.json").read_text(encoding="utf-8"))
            _append_audit("package", [str(args.package_dir)], [str(output)], qc_result, metadata["seed"])
            print(f"Rendered {output} with {len(manifest['documents'])} listed synthetic sources. QC: {'PASS' if qc_result['passed'] else 'FAIL'}.")
            print(provenance_banner(manifest))
            return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ee {args.command} failed: {exc}", file=sys.stderr)
        return 2
    parser.error("unknown command")
    return 2
