# PDF Production and Visual QA

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

## Visual inspection

Render every page:

```bash
mkdir -p tmp/rendered-pages
pdftoppm -png -r 140 output/pdf/formal-plan.pdf tmp/rendered-pages/page
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

## Kroki Mermaid boundary

The public Kroki Mermaid endpoint returns PNG or SVG, not PDF. Prefer one SVG
request, then convert that SVG locally to both PNG and PDF with CairoSVG,
`rsvg-convert`, Inkscape, or Chrome/Chromium. This avoids multiple external
render calls and keeps all delivered formats derived from one rendering. Do not
call `/mermaid/pdf` and misclassify its unsupported-format response as invalid
Mermaid source.
