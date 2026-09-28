import json
import subprocess
import sys
from pathlib import Path

from editorial_engine import cli
from editorial_engine.rendering import render_package


def test_html_bundle_has_a_provenance_banner_on_every_page(package):
    path = render_package(package, "html")
    document = path.read_text(encoding="utf-8")
    assert "no generative model" in document
    assert document.count('class="page"') == document.count('class="provenance"')
    assert document.count('class="page"') >= 6
    assert "<img alt=" in document


def test_cli_smoke_and_audit_trail(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "AUDIT_PATH", tmp_path / "ee-audit.jsonl")
    sources, package = tmp_path / "sources", tmp_path / "package"
    assert cli.main(["fixtures", "--out", str(sources)]) == 0
    output = capsys.readouterr().out
    assert "synthetic sources" in output and "no generative model" in output
    assert cli.main(["assemble", "--sources", str(sources), "--out", str(package)]) == 0
    assert cli.main(["citations", str(package)]) == 0
    assert cli.main(["qc", str(package)]) == 0
    assert cli.main(["package", str(package), "--format", "html"]) == 0
    audit = [json.loads(line) for line in (tmp_path / "ee-audit.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [row["subcommand"] for row in audit] == ["fixtures", "assemble", "citations", "qc", "package"]
    assert all(row["seed"] == 17 and row["timestamp"] and row["outputs"] for row in audit)
    assert audit[-1]["qc_results"]["passed"]
    assert (package / "package.html").is_file()


def test_markdown_package_contains_page_banners(package):
    path = render_package(package, "md")
    document = path.read_text(encoding="utf-8")
    assert document.count("Provenance: all content on this page") >= 6
    assert "QC report" in document
    assert "Citation report" in document


def test_python_module_cli_entrypoint(tmp_path):
    root = Path(__file__).resolve().parents[1]
    out = tmp_path / "cli-sources"
    result = subprocess.run(
        [sys.executable, "-m", "editorial_engine", "fixtures", "--out", str(out)],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    assert "no generative model" in result.stdout
    assert (out / "fixture_manifest.json").is_file()
