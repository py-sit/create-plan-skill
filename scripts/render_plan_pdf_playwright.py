#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import base64
import hashlib
from html import escape
import mimetypes
from pathlib import Path
import re
import shutil
from typing import Any
from urllib.parse import unquote, urlparse

try:
    import markdown
    from markdown.extensions import Extension
    from markdown.treeprocessors import Treeprocessor
    from pypdf import PdfReader
    import yaml
except ImportError as error:
    raise RuntimeError(
        "Missing V2 dependency. Install scripts/requirements-v2.txt."
    ) from error


SKILL_ROOT = Path(__file__).resolve().parents[1]
THEMES_ROOT = SKILL_ROOT / "shared" / "themes"
DEFAULT_THEME = "corporate-blue"
ALLOWED_EXTERNAL_SCHEMES = {"https", "http", "mailto", "tel"}
RAW_HTML_PATTERN = re.compile(r"</?[A-Za-z][^>\\n]*>")


class RendererUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class RenderResult:
    pdf: Path
    html: Path
    pages: int
    sha256: str
    theme: str


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    metadata: dict[str, str] = {}
    closing: int | None = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            closing = index
            break
        if ":" not in lines[index]:
            continue
        key, value = lines[index].split(":", 1)
        metadata[key.strip()] = value.strip().strip('"').strip("'")
    if closing is None:
        raise ValueError("Unclosed YAML frontmatter")
    return metadata, "\n".join(lines[closing + 1 :])


def escape_raw_html(text: str) -> str:
    return RAW_HTML_PATTERN.sub(lambda match: escape(match.group(0)), text)


def is_relative_target(target: str) -> bool:
    parsed = urlparse(target)
    return not parsed.scheme and not target.startswith(("/", "\\"))


def within_workspace(path: Path, workspace: Path) -> bool:
    try:
        path.relative_to(workspace)
        return True
    except ValueError:
        return False


def image_data_uri(source: Path) -> str:
    mime, _ = mimetypes.guess_type(source.name)
    if not mime or not mime.startswith("image/"):
        raise ValueError(f"Unsupported image type: {source}")
    encoded = base64.b64encode(source.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


class SafeLinkTreeprocessor(Treeprocessor):
    def __init__(self, md: markdown.Markdown, workspace: Path) -> None:
        super().__init__(md)
        self.workspace = workspace

    def run(self, root: Any) -> Any:
        for element in root.iter():
            if element.tag == "a":
                href = str(element.attrib.get("href", "")).strip()
                scheme = urlparse(href).scheme.lower()
                if scheme in ALLOWED_EXTERNAL_SCHEMES or href.startswith("#"):
                    element.attrib["rel"] = "noreferrer"
                    continue
                element.tag = "span"
                element.attrib.clear()
                element.attrib["class"] = "local-reference"
                if href:
                    element.attrib["data-reference"] = unquote(href)
            elif element.tag == "img":
                src = str(element.attrib.get("src", "")).strip()
                if not is_relative_target(src):
                    element.tag = "span"
                    element.text = f"[external image blocked: {src}]"
                    element.attrib.clear()
                    element.attrib["class"] = "blocked-image"
                    continue
                resolved = (self.workspace / unquote(src)).resolve()
                if not within_workspace(resolved, self.workspace):
                    raise ValueError(f"Image escapes workspace boundary: {src}")
                if not resolved.is_file():
                    raise FileNotFoundError(f"Image not found: {resolved}")
                element.attrib["src"] = image_data_uri(resolved)
        return root


class SafeLinkExtension(Extension):
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        super().__init__()

    def extendMarkdown(self, md: markdown.Markdown) -> None:
        md.treeprocessors.register(
            SafeLinkTreeprocessor(md, self.workspace),
            "create-plan-safe-links",
            5,
        )


def render_markdown(body: str, workspace: Path) -> tuple[str, str]:
    converter = markdown.Markdown(
        extensions=[
            "tables",
            "fenced_code",
            "sane_lists",
            "toc",
            SafeLinkExtension(workspace),
        ],
        extension_configs={
            "toc": {
                "permalink": False,
                "toc_depth": "2-3",
            }
        },
        output_format="html5",
    )
    html = converter.convert(escape_raw_html(body))
    return html, converter.toc


def load_source_register(workspace: Path) -> list[dict[str, Any]]:
    path = workspace / "source-register.yaml"
    if not path.is_file():
        return []
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    sources = payload.get("sources", [])
    if not isinstance(sources, list):
        raise ValueError("source-register.yaml sources must be a list")
    return [source for source in sources if isinstance(source, dict)]


def source_appendix(
    sources: list[dict[str, Any]],
    language: str,
    workspace: Path,
) -> str:
    if not sources:
        return ""
    heading = "参考资料" if language == "zh-CN" else "References"
    rows: list[str] = []
    for source in sources:
        source_id = escape(str(source.get("id", "")))
        title = escape(str(source.get("title", "")))
        kind = escape(str(source.get("kind", "")))
        publisher = escape(str(source.get("publisher", "")))
        accessed = escape(str(source.get("accessed", "")))
        version = escape(str(source.get("version", "")))
        license_name = escape(str(source.get("license", "")))
        supports = ", ".join(
            escape(str(value))
            for value in source.get("supports", [])
            if isinstance(value, str)
        )
        url = str(source.get("url", "")).strip()
        local_path = str(source.get("local_path", "")).strip()
        if local_path:
            candidate = (workspace / local_path).resolve()
            if not is_relative_target(local_path) or not within_workspace(
                candidate,
                workspace,
            ):
                raise ValueError(
                    f"Source local_path must be workspace-relative: {source_id}"
                )
            reference = f"<code>{escape(local_path)}</code>"
        elif urlparse(url).scheme.lower() == "https":
            safe_url = escape(url, quote=True)
            reference = f'<a href="{safe_url}" rel="noreferrer">{safe_url}</a>'
        else:
            reference = ""
        rows.append(
            "<tr>"
            f"<td>{source_id}</td>"
            f"<td><strong>{title}</strong><br><span>{reference}</span></td>"
            f"<td>{kind}</td>"
            f"<td>{publisher}</td>"
            f"<td>{version}</td>"
            f"<td>{accessed}</td>"
            f"<td>{license_name}</td>"
            f"<td>{supports}</td>"
            "</tr>"
        )
    return (
        '<section class="source-appendix">'
        f"<h2>{heading}</h2>"
        "<table><thead><tr>"
        "<th>ID</th><th>Source</th><th>Kind</th><th>Publisher</th>"
        "<th>Version</th><th>Accessed</th><th>License</th><th>Evidence</th>"
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></section>"
    )


def load_theme(theme: str) -> tuple[str, str]:
    normalized = theme.strip().lower()
    if not re.fullmatch(r"[a-z0-9-]+", normalized):
        raise ValueError(f"Invalid theme name: {theme}")
    path = THEMES_ROOT / f"{normalized}.css"
    if not path.is_file():
        available = ", ".join(sorted(item.stem for item in THEMES_ROOT.glob("*.css")))
        raise ValueError(f"Unknown theme: {normalized}. Available: {available}")
    return normalized, path.read_text(encoding="utf-8")


def manifest_theme(workspace: Path) -> str:
    path = workspace / "plan-manifest.yaml"
    if not path.is_file():
        return DEFAULT_THEME
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    value = payload.get("theme", DEFAULT_THEME)
    return str(value) if value else DEFAULT_THEME


def browser_candidates(explicit: Path | None) -> list[Path]:
    candidates: list[Path] = []
    if explicit:
        candidates.append(explicit)
    for command in ("google-chrome", "chromium", "chromium-browser"):
        found = shutil.which(command)
        if found:
            candidates.append(Path(found))
    candidates.extend(
        [
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
        ]
    )
    return [candidate for candidate in candidates if candidate.is_file()]


def build_html(
    metadata: dict[str, str],
    content_html: str,
    toc_html: str,
    appendix_html: str,
    theme_css: str,
    language: str,
) -> str:
    title = escape(metadata.get("title", "Formal Plan"))
    subtitle = escape(metadata.get("subtitle", ""))
    status = escape(
        metadata.get(
            "status",
            "方案评审稿" if language == "zh-CN" else "Draft for Review",
        )
    )
    version = escape(metadata.get("version", "V2.0"))
    document_date = escape(metadata.get("date", date.today().isoformat()))
    scope = escape(
        metadata.get(
            "scope",
            "本轮只输出设计"
            if language == "zh-CN"
            else "This phase delivers design only",
        )
    )
    recommendation_label = "推荐方案" if language == "zh-CN" else "Recommended approach"
    contents_label = "目录" if language == "zh-CN" else "Contents"
    review_gate = (
        "评审确认后，再进入实施计划或 PoC 阶段"
        if language == "zh-CN"
        else "Proceed to implementation planning or PoC only after review approval"
    )
    base_css = """
html, body {
  margin: 0;
  padding: 0;
  color: var(--text-color);
  background: var(--page-background);
  font-family: var(--font-stack);
  font-size: 9.6pt;
  line-height: 1.62;
}
body { orphans: 3; widows: 3; }
.cover {
  min-height: 257mm;
  page-break-after: always;
  display: flex;
  flex-direction: column;
}
.cover-band {
  margin: -17mm -18mm 18mm;
  min-height: 92mm;
  padding: 30mm 22mm 18mm;
  color: white;
  background: linear-gradient(135deg, var(--brand-color), var(--accent-color));
  display: flex;
  flex-direction: column;
  justify-content: center;
  text-align: center;
}
.cover h1 { margin: 0; font-size: 28pt; line-height: 1.25; }
.subtitle { margin-top: 6mm; font-size: 12pt; opacity: .9; }
.recommendation {
  margin: 0 auto 12mm;
  width: 82%;
  padding: 6mm;
  border: 1px solid var(--accent-color);
  border-radius: 3mm;
  background: var(--panel-color);
}
.recommendation strong { color: var(--brand-color); }
.meta-grid {
  width: 72%;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 2mm 5mm;
}
.meta-grid dt { color: var(--muted-color); }
.meta-grid dd { margin: 0; }
.review-gate {
  margin-top: auto;
  padding-top: 5mm;
  border-top: 2px solid var(--accent-color);
  text-align: center;
  color: var(--brand-color);
  font-weight: 600;
}
.toc { page-break-after: always; }
.toc h2 { font-size: 22pt; }
.toc ul { list-style: none; padding-left: 0; }
.toc li { padding: 2.2mm 0; border-bottom: 1px solid var(--line-color); }
.toc li li { margin-left: 7mm; font-size: 9pt; }
.toc a { color: var(--brand-color); text-decoration: none; }
main h2, main h3, main h4 { page-break-after: avoid; color: var(--brand-color); }
main h2 {
  margin: 8mm 0 3mm;
  padding-bottom: 2mm;
  border-bottom: 1px solid var(--line-color);
  font-size: 18pt;
}
main h3 { margin: 5mm 0 2mm; font-size: 13pt; }
main h4 { margin: 4mm 0 1mm; font-size: 10.5pt; }
p, li { overflow-wrap: anywhere; }
ul, ol { padding-left: 7mm; }
blockquote {
  margin: 4mm 0;
  padding: 3mm 5mm;
  border-left: 1.2mm solid var(--accent-color);
  background: var(--panel-color);
}
code {
  font-family: "SFMono-Regular", Consolas, monospace;
  color: #9a3412;
  background: var(--panel-color);
  padding: .2mm .8mm;
  border-radius: 1mm;
}
pre {
  page-break-inside: avoid;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  padding: 4mm;
  border: 1px solid var(--line-color);
  background: var(--panel-color);
}
pre code { color: inherit; background: transparent; padding: 0; }
table {
  width: 100%;
  margin: 4mm 0;
  border-collapse: collapse;
  table-layout: fixed;
  font-size: 7.6pt;
}
thead { display: table-header-group; }
tr { page-break-inside: avoid; }
th, td {
  padding: 2.1mm;
  border: .25mm solid var(--line-color);
  vertical-align: top;
  overflow-wrap: anywhere;
}
th { color: var(--brand-color); background: var(--table-header); }
tbody tr:nth-child(even) { background: var(--table-alt); }
img {
  display: block;
  max-width: 100%;
  max-height: 115mm;
  margin: 4mm auto;
  object-fit: contain;
}
a { color: var(--brand-color); text-decoration: underline; }
.local-reference {
  color: var(--brand-color);
  text-decoration: underline;
}
.blocked-image {
  display: block;
  padding: 3mm;
  border: 1px dashed var(--line-color);
  color: var(--muted-color);
}
.source-appendix { page-break-before: always; }
.source-appendix table { font-size: 6.7pt; }
"""
    recommendation = escape(metadata.get("recommendation", ""))
    recommendation_html = (
        f'<div class="recommendation"><strong>{recommendation_label}</strong>'
        f"<br>{recommendation}</div>"
        if recommendation
        else ""
    )
    return f"""<!doctype html>
<html lang="{escape(language)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>{theme_css}\n{base_css}</style>
</head>
<body>
  <section class="cover">
    <div class="cover-band">
      <h1>{title}</h1>
      <div class="subtitle">{subtitle}</div>
    </div>
    {recommendation_html}
    <dl class="meta-grid">
      <dt>{"文档状态" if language == "zh-CN" else "Document status"}</dt><dd>{status}</dd>
      <dt>{"版本" if language == "zh-CN" else "Version"}</dt><dd>{version}</dd>
      <dt>{"日期" if language == "zh-CN" else "Date"}</dt><dd>{document_date}</dd>
      <dt>{"方案边界" if language == "zh-CN" else "Scope boundary"}</dt><dd>{scope}</dd>
    </dl>
    <div class="review-gate">{review_gate}</div>
  </section>
  <nav class="toc"><h2>{contents_label}</h2>{toc_html}</nav>
  <main>{content_html}{appendix_html}</main>
</body>
</html>
"""


def update_manifest(
    workspace: Path,
    output: Path,
    html_output: Path,
    theme: str,
    digest: str,
) -> None:
    path = workspace / "plan-manifest.yaml"
    if not path.is_file():
        return
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    render_data = payload.setdefault("render", {})
    render_data["engine"] = "playwright"
    payload["theme"] = theme
    payload["stage"] = "authoring"
    artifacts = payload.setdefault("artifacts", {})
    for key, artifact in (
        ("pdf", output),
        ("html", html_output),
    ):
        try:
            artifacts[key] = str(artifact.relative_to(workspace))
        except ValueError:
            artifacts[key] = artifact.name
    artifacts["pdf_sha256"] = digest
    path.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def render(
    proposal: Path,
    output: Path,
    theme: str | None = None,
    html_output: Path | None = None,
    browser_executable: Path | None = None,
) -> RenderResult:
    if not proposal.is_file():
        raise FileNotFoundError(f"Proposal not found: {proposal}")
    workspace = proposal.parent.resolve()
    metadata, body = parse_frontmatter(proposal.read_text(encoding="utf-8"))
    language = metadata.get("language", "zh-CN")
    if language not in {"zh-CN", "en-US"}:
        raise ValueError(f"Unsupported language: {language}")
    selected_theme, theme_css = load_theme(theme or manifest_theme(workspace))
    content_html, toc_html = render_markdown(body, workspace)
    appendix_html = source_appendix(
        load_source_register(workspace),
        language,
        workspace,
    )
    html = build_html(
        metadata,
        content_html,
        toc_html,
        appendix_html,
        theme_css,
        language,
    )
    if html_output is None:
        html_output = workspace / "output" / "html" / "formal-plan.html"
    html_output.parent.mkdir(parents=True, exist_ok=True)
    html_output.write_text(html, encoding="utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise RendererUnavailable(
            "Playwright is not installed. Install scripts/requirements-v2.txt."
        ) from error

    executable_candidates = browser_candidates(browser_executable)
    with sync_playwright() as playwright:
        launch_options: dict[str, Any] = {"headless": True}
        if executable_candidates:
            launch_options["executable_path"] = str(executable_candidates[0])
        try:
            browser = playwright.chromium.launch(**launch_options)
        except Exception as error:
            raise RendererUnavailable(
                "Chromium could not start. Run `python -m playwright install chromium` "
                "or pass --browser-executable."
            ) from error
        try:
            page = browser.new_page()
            page.route(
                re.compile(r"^https?://"),
                lambda route: route.abort(),
            )
            page.set_content(html, wait_until="load")
            page.evaluate("document.fonts.ready")
            page.pdf(
                path=str(output),
                format="A4",
                print_background=True,
                prefer_css_page_size=True,
                display_header_footer=True,
                header_template="<span></span>",
                footer_template=(
                    '<div style="width:100%;font-size:7px;color:#61738b;'
                    'padding:0 18mm;text-align:right">'
                    '<span class="pageNumber"></span> / '
                    '<span class="totalPages"></span></div>'
                ),
                margin={
                    "top": "0",
                    "right": "0",
                    "bottom": "8mm",
                    "left": "0",
                },
                tagged=True,
                outline=True,
            )
        finally:
            browser.close()

    if not output.is_file() or not output.read_bytes().startswith(b"%PDF"):
        raise RuntimeError(f"Playwright produced an invalid PDF: {output}")
    reader = PdfReader(str(output))
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    update_manifest(workspace, output, html_output, selected_theme, digest)
    return RenderResult(
        pdf=output,
        html=html_output,
        pages=len(reader.pages),
        sha256=digest,
        theme=selected_theme,
    )
