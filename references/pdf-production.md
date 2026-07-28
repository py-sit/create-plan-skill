# PDF Production and Visual QA

## Contents

- Source and output separation
- Environment preflight
- Language
- Typography and layout
- Visual inspection
- Delivery verification
- Kroki Mermaid boundary

## Source and output separation

Use:

```text
proposal-workspace/
├── proposal.md
├── evidence-register.md
├── decision-log.md
├── assets/
├── diagrams/
│   ├── architecture.mmd
│   └── rendered/
├── output/pdf/
└── tmp/rendered-pages/
```

Never overwrite supplied source files. Keep generated artifacts in `output/` and temporary previews in `tmp/`.

## Environment preflight

Run before the first full proposal build on a machine:

```bash
python3 scripts/check_environment.py
```

Use `--json` for machine-readable capability data and `--strict` when local PDF
page rendering and fonts are mandatory. A missing local `mmdc` is not silently
replaced with a public service; Kroki still requires explicit
`--allow-network`.

## Language

Initialize the workspace with an explicit language:

```bash
python3 scripts/init_plan_workspace.py \
  --output-dir /absolute/path/to/workspace \
  --title "方案名称" \
  --language zh-CN
```

Supported values are `zh-CN` and `en-US`. The language controls the source
template, cover labels, status labels, table-of-contents title, review gate,
and page numbering. Do not claim English PDF support when only the body text
has been translated.

## Typography

- Embed a font that supports all required Chinese and Latin glyphs.
- Do not treat successful text extraction as proof of visible glyphs.
- Use consistent title, heading, body, caption, and table styles.
- Avoid fonts that render blank in the target PDF renderer.

## Layout

- Use A4 unless the user or template requires another size.
- Keep cover title entirely inside its visual region.
- Avoid duplicate numbering in the table of contents.
- Keep diagrams readable without zooming beyond normal review.
- Allow table rows to split only when readability remains acceptable.
- Do not place a heading as the final line of a page.
- Use stable header, footer, page number, version, and document title.
- Keep external HTTP(S) citations clickable. Render local Markdown references as
  visible labels only; never embed temporary absolute `file://` paths in a
  delivered PDF.

## Visual inspection

Render every page:

```bash
python3 scripts/render_pdf_pages.py output/pdf/formal-plan.pdf \
  --output-dir tmp/rendered-pages
python3 scripts/create_pdf_contact_sheet.py tmp/rendered-pages \
  --output tmp/contact-sheet.png
```

Inspect:

- cover;
- contents;
- every diagram page;
- every table;
- dense text pages;
- final recommendation page;
- all remaining pages through contact sheets.

Reject the PDF if any page has:

- missing or blank Chinese text;
- clipping or overlap;
- unreadably small diagrams;
- broken image aspect ratio;
- black squares or missing glyphs;
- table text outside cells;
- duplicated or incorrect numbering;
- stale placeholders;
- blank pages without intent.

## Delivery verification

After copying the PDF:

```bash
shasum -a 256 source.pdf delivered.pdf
```

The hashes must match. Report page count, file size, hash, and destination.

The full-proposal validator can verify the rendered page count and delivered
copy in one pass:

```bash
python3 scripts/validate_plan_package.py \
  --mode full-proposal \
  --workspace /absolute/path/to/workspace \
  --rendered-pages-dir /absolute/path/to/workspace/tmp/rendered-pages \
  --delivered-pdf /absolute/path/to/delivered.pdf
```

## Kroki Mermaid boundary

The public Kroki Mermaid endpoint returns PNG or SVG, not PDF. Prefer one SVG
request, then convert that SVG locally to both PNG and PDF with CairoSVG,
`rsvg-convert`, Inkscape, or Chrome/Chromium. This avoids multiple external
render calls and keeps all delivered formats derived from one rendering. Do not
call `/mermaid/pdf` and misclassify its unsupported-format response as invalid
Mermaid source.
