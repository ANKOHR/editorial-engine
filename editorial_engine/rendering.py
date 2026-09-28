"""Render assembled editorial pages into a Markdown or HTML bundle."""

import html
import re
from pathlib import Path


def _markdown_to_html(markdown: str) -> str:
    output = []
    in_list = False
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line:
            if in_list:
                output.append("</ul>")
                in_list = False
            continue
        if line.startswith("> "):
            output.append(f'<p class="provenance">{html.escape(line[2:])}</p>')
        elif line.startswith(("### ", "## ", "# ")):
            level = len(line) - len(line.lstrip("#"))
            output.append(f"<h{level}>{html.escape(line[level + 1:])}</h{level}>")
        elif line.startswith("- "):
            if not in_list:
                output.append("<ul>")
                in_list = True
            output.append(f"<li>{_inline(line[2:])}</li>")
        else:
            if in_list:
                output.append("</ul>")
                in_list = False
            output.append(f"<p>{_inline(line)}</p>")
    if in_list:
        output.append("</ul>")
    return "\n".join(output)


def _inline(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", escaped)
    escaped = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img alt="\1" src="\2">', escaped)
    escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', escaped)
    return escaped


def render_package(package_dir: Path, output_format: str) -> Path:
    package_dir = Path(package_dir)
    if output_format not in {"md", "html"}:
        raise ValueError("format must be md or html")
    pages = [path for path in sorted(package_dir.glob("*.md")) if path.name != "package.md"]
    if not pages:
        raise ValueError(f"No Markdown pages found in {package_dir}")
    if output_format == "md":
        parts = []
        for page in pages:
            parts.extend([page.read_text(encoding="utf-8").rstrip(), "\n\n---\n"])
        destination = package_dir / "package.md"
        destination.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8", newline="\n")
        return destination
    sections = []
    for page in pages:
        rendered = _markdown_to_html(page.read_text(encoding="utf-8"))
        sections.append(f'<section class="page" id="{html.escape(page.stem)}">{rendered}</section>')
    document = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Editorial Engine synthetic fixture package</title>
<style>
body{font-family:Arial,sans-serif;max-width:920px;margin:0 auto;padding:2rem;color:#182b36;background:#fbfaf7;line-height:1.55}
.page{padding:2rem 0;border-bottom:1px solid #c8d0d2;min-height:60vh;page-break-after:always}
.provenance{padding:1rem;background:#e4efed;border-left:4px solid #327c78;font-size:.9rem}
li{margin:.35rem 0}img{max-width:100%;height:auto}code{background:#edf0ef;padding:.1rem .3rem}
@media print{body{max-width:none}.page{break-after:page}}
</style>
</head>
<body>
<h1>Editorial Engine synthetic fixture package</h1>
""" + "\n".join(sections) + "\n</body>\n</html>\n"
    destination = package_dir / "package.html"
    destination.write_text(document, encoding="utf-8", newline="\n")
    return destination
