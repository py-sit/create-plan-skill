#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date
from html import escape
import hashlib
from pathlib import Path
import re
import sys
from typing import Dict, List, Sequence, Tuple

try:
    from PIL import Image as PillowImage
    from pypdf import PdfReader, PdfWriter
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas
    from reportlab.platypus import (
        Image,
        KeepTogether,
        ListFlowable,
        ListItem,
        PageBreak,
        Paragraph,
        Preformatted,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
except ImportError as error:
    print(
        "ERROR: Missing dependency. Install reportlab, pypdf, and Pillow.",
        file=sys.stderr,
    )
    raise SystemExit(2) from error


PAGE_WIDTH, PAGE_HEIGHT = A4
BLUE = colors.HexColor("#174474")
ACCENT = colors.HexColor("#2F6FED")
LIGHT_BLUE = colors.HexColor("#EAF2FC")
TEXT = colors.HexColor("#23354D")
MUTED = colors.HexColor("#61738B")
LINE = colors.HexColor("#C9D8EA")
TABLE_HEADER = colors.HexColor("#DCE9F8")
TABLE_ALT = colors.HexColor("#F7FAFE")


def parse_frontmatter(text: str) -> Tuple[Dict[str, str], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    metadata: Dict[str, str] = {}
    closing = None
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


def find_font(explicit: Path | None) -> Path:
    candidates: List[Path] = []
    if explicit:
        candidates.append(explicit.expanduser())
    candidates.extend(
        [
            Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
            Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
            Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
        ]
    )
    for candidate in candidates:
        if candidate.is_file() and candidate.suffix.lower() == ".ttf":
            return candidate.resolve()
    raise FileNotFoundError(
        "No compatible Chinese TTF font found. Pass --font /absolute/path/font.ttf"
    )


def inline_markup(value: str, font_name: str) -> str:
    escaped = escape(value.strip())
    escaped = re.sub(
        r"`([^`]+)`",
        rf'<font name="{font_name}" color="#9A3412">\1</font>',
        escaped,
    )
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)
    return escaped


def load_styles(font_name: str) -> Dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=9.5,
            leading=15,
            textColor=TEXT,
            spaceAfter=7,
            wordWrap="CJK",
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading1"],
            fontName=font_name,
            fontSize=18,
            leading=23,
            textColor=BLUE,
            spaceBefore=10,
            spaceAfter=9,
            keepWithNext=True,
            wordWrap="CJK",
        ),
        "h3": ParagraphStyle(
            "H3",
            parent=base["Heading2"],
            fontName=font_name,
            fontSize=13,
            leading=18,
            textColor=colors.HexColor("#1762A8"),
            spaceBefore=8,
            spaceAfter=6,
            keepWithNext=True,
            wordWrap="CJK",
        ),
        "h4": ParagraphStyle(
            "H4",
            parent=base["Heading3"],
            fontName=font_name,
            fontSize=10.5,
            leading=15,
            textColor=BLUE,
            spaceBefore=6,
            spaceAfter=4,
            keepWithNext=True,
            wordWrap="CJK",
        ),
        "toc_title": ParagraphStyle(
            "TocTitle",
            fontName=font_name,
            fontSize=22,
            leading=28,
            textColor=BLUE,
            spaceAfter=16,
        ),
        "toc_item": ParagraphStyle(
            "TocItem",
            fontName=font_name,
            fontSize=10,
            leading=16,
            textColor=TEXT,
            leftIndent=8,
            spaceAfter=4,
            wordWrap="CJK",
        ),
        "caption": ParagraphStyle(
            "Caption",
            fontName=font_name,
            fontSize=8,
            leading=11,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        "table": ParagraphStyle(
            "Table",
            fontName=font_name,
            fontSize=7.5,
            leading=10,
            textColor=TEXT,
            wordWrap="CJK",
        ),
        "code": ParagraphStyle(
            "Code",
            fontName=font_name,
            fontSize=7.5,
            leading=10,
            textColor=TEXT,
            backColor=colors.HexColor("#F3F6FA"),
            borderPadding=6,
        ),
    }


def image_flowables(
    markdown_path: Path,
    alt_text: str,
    target: str,
    styles: Dict[str, ParagraphStyle],
) -> List[object]:
    image_path = (markdown_path.parent / target).resolve()
    if not image_path.is_file():
        raise FileNotFoundError(f"Image not found: {image_path}")
    if image_path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
        raise ValueError(
            f"PDF renderer supports PNG/JPG images. Render this asset first: {image_path}"
        )
    with PillowImage.open(image_path) as source:
        width, height = source.size
    max_width = 165 * mm
    max_height = 105 * mm
    scale = min(max_width / width, max_height / height, 1.0)
    image = Image(str(image_path), width=width * scale, height=height * scale)
    image.hAlign = "CENTER"
    return [
        Spacer(1, 4),
        image,
        Paragraph(escape(alt_text), styles["caption"]),
    ]


def parse_table(
    lines: Sequence[str],
    start: int,
    styles: Dict[str, ParagraphStyle],
    font_name: str,
) -> Tuple[Table, int]:
    rows: List[List[str]] = []
    index = start
    while index < len(lines) and lines[index].strip().startswith("|"):
        cells = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
        rows.append(cells)
        index += 1
    if len(rows) < 2:
        raise ValueError("Markdown table requires a header and separator row")
    separator = rows[1]
    if not all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in separator):
        raise ValueError("Invalid Markdown table separator")
    data_rows = [rows[0]] + rows[2:]
    column_count = max(len(row) for row in data_rows)
    normalized = [row + [""] * (column_count - len(row)) for row in data_rows]
    data = [
        [Paragraph(inline_markup(cell, font_name), styles["table"]) for cell in row]
        for row in normalized
    ]
    available = 175 * mm
    widths = [available / column_count] * column_count
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), TABLE_HEADER),
        ("TEXTCOLOR", (0, 0), (-1, 0), BLUE),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#86A9D1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for row_index in range(1, len(data)):
        if row_index % 2 == 0:
            commands.append(("BACKGROUND", (0, row_index), (-1, row_index), TABLE_ALT))
    table.setStyle(TableStyle(commands))
    return table, index


def paragraph_from_buffer(
    buffer: List[str],
    styles: Dict[str, ParagraphStyle],
    font_name: str,
) -> List[object]:
    if not buffer:
        return []
    text = " ".join(part.strip() for part in buffer).strip()
    buffer.clear()
    if not text:
        return []
    return [Paragraph(inline_markup(text, font_name), styles["body"])]


def parse_markdown(
    markdown_path: Path,
    body: str,
    styles: Dict[str, ParagraphStyle],
    font_name: str,
) -> Tuple[List[object], List[str]]:
    lines = body.splitlines()
    story: List[object] = []
    headings: List[str] = []
    paragraph_buffer: List[str] = []
    index = 0

    while index < len(lines):
        raw = lines[index]
        stripped = raw.strip()
        if not stripped:
            story.extend(paragraph_from_buffer(paragraph_buffer, styles, font_name))
            index += 1
            continue

        if stripped.startswith("```"):
            story.extend(paragraph_from_buffer(paragraph_buffer, styles, font_name))
            code_lines: List[str] = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(lines[index])
                index += 1
            story.append(Preformatted("\n".join(code_lines), styles["code"]))
            index += 1
            continue

        image_match = re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", stripped)
        if image_match:
            story.extend(paragraph_from_buffer(paragraph_buffer, styles, font_name))
            story.extend(
                image_flowables(
                    markdown_path,
                    image_match.group(1) or "图",
                    image_match.group(2),
                    styles,
                )
            )
            index += 1
            continue

        if stripped.startswith("|"):
            story.extend(paragraph_from_buffer(paragraph_buffer, styles, font_name))
            table, index = parse_table(lines, index, styles, font_name)
            story.extend([Spacer(1, 4), table, Spacer(1, 8)])
            continue

        heading_match = re.match(r"^(#{1,4})\s+(.+)$", stripped)
        if heading_match:
            story.extend(paragraph_from_buffer(paragraph_buffer, styles, font_name))
            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()
            if level == 1:
                index += 1
                continue
            if level == 2:
                headings.append(title)
                story.append(Spacer(1, 3))
                story.append(Paragraph(inline_markup(title, font_name), styles["h2"]))
            elif level == 3:
                story.append(Paragraph(inline_markup(title, font_name), styles["h3"]))
            else:
                story.append(Paragraph(inline_markup(title, font_name), styles["h4"]))
            index += 1
            continue

        if stripped == "---":
            story.extend(paragraph_from_buffer(paragraph_buffer, styles, font_name))
            story.append(Spacer(1, 4))
            index += 1
            continue

        if re.match(r"^[-*]\s+", stripped) or re.match(r"^\d+\.\s+", stripped):
            story.extend(paragraph_from_buffer(paragraph_buffer, styles, font_name))
            ordered = bool(re.match(r"^\d+\.\s+", stripped))
            items: List[ListItem] = []
            while index < len(lines):
                current = lines[index].strip()
                pattern = r"^\d+\.\s+(.+)$" if ordered else r"^[-*]\s+(.+)$"
                match = re.match(pattern, current)
                if not match:
                    break
                items.append(
                    ListItem(
                        Paragraph(inline_markup(match.group(1), font_name), styles["body"]),
                        leftIndent=12,
                    )
                )
                index += 1
            list_options = {
                "leftIndent": 18,
                "bulletFontName": font_name,
                "bulletFontSize": 8,
                "spaceAfter": 5,
            }
            if ordered:
                story.append(
                    ListFlowable(
                        items,
                        bulletType="1",
                        start="1",
                        bulletFormat="%s.",
                        **list_options,
                    )
                )
            else:
                story.append(
                    ListFlowable(
                        items,
                        bulletType="bullet",
                        start="•",
                        **list_options,
                    )
                )
            continue

        paragraph_buffer.append(stripped)
        index += 1

    story.extend(paragraph_from_buffer(paragraph_buffer, styles, font_name))
    return story, headings


def make_cover(path: Path, metadata: Dict[str, str], font_name: str) -> None:
    pdf = canvas.Canvas(str(path), pagesize=A4)
    title = metadata.get("title", "正式方案")
    subtitle = metadata.get("subtitle", "")
    recommendation = metadata.get("recommendation", "")
    pdf.setTitle(title)
    pdf.setAuthor("Created with create-plan-skill")
    pdf.setFillColor(BLUE)
    pdf.rect(0, PAGE_HEIGHT - 300, PAGE_WIDTH, 300, fill=1, stroke=0)
    pdf.setFillColor(colors.HexColor("#DCEAFF"))
    pdf.circle(PAGE_WIDTH - 63, PAGE_HEIGHT - 64, 27, fill=1, stroke=0)
    pdf.setFillColor(colors.white)
    title_size = 27.0
    maximum_title_width = PAGE_WIDTH - 92 * mm
    measured_width = pdfmetrics.stringWidth(title, font_name, title_size)
    if measured_width > maximum_title_width:
        title_size = max(15.0, title_size * maximum_title_width / measured_width)
    pdf.setFont(font_name, title_size)
    pdf.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT - 150, title)
    if subtitle:
        pdf.setFont(font_name, 11.5)
        pdf.setFillColor(colors.HexColor("#D7E7FF"))
        pdf.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT - 190, subtitle)
    if recommendation:
        pdf.setFillColor(LIGHT_BLUE)
        pdf.setStrokeColor(colors.HexColor("#5B91E8"))
        pdf.roundRect(78, PAGE_HEIGHT - 382, PAGE_WIDTH - 156, 58, 4, fill=1, stroke=1)
        pdf.setFillColor(BLUE)
        pdf.setFont(font_name, 10.5)
        pdf.drawString(100, PAGE_HEIGHT - 349, "推荐方案")
        pdf.setFont(font_name, 10.5)
        text = recommendation[:54] + ("…" if len(recommendation) > 54 else "")
        pdf.drawString(100, PAGE_HEIGHT - 370, text)
    pdf.setFillColor(TEXT)
    pdf.setFont(font_name, 10)
    meta_lines = [
        f"文档状态：{metadata.get('status', '方案评审稿')}",
        f"版本：{metadata.get('version', 'V1.0')}",
        f"日期：{metadata.get('date', date.today().isoformat())}",
        f"方案边界：{metadata.get('scope', '本轮只输出设计')}",
    ]
    y = PAGE_HEIGHT - 455
    for line in meta_lines:
        pdf.drawCentredString(PAGE_WIDTH / 2, y, line)
        y -= 24
    pdf.setStrokeColor(ACCENT)
    pdf.line(122, 132, PAGE_WIDTH - 122, 132)
    pdf.setFillColor(BLUE)
    pdf.setFont(font_name, 9)
    pdf.drawCentredString(PAGE_WIDTH / 2, 112, "评审确认后，再进入实施计划或 PoC 阶段")
    pdf.showPage()
    pdf.save()


def make_body(
    path: Path,
    metadata: Dict[str, str],
    content: List[object],
    headings: List[str],
    styles: Dict[str, ParagraphStyle],
    font_name: str,
) -> None:
    title = metadata.get("title", "正式方案")
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=17 * mm,
        title=title,
        author="Created with create-plan-skill",
    )

    def header_footer(pdf: canvas.Canvas, document: SimpleDocTemplate) -> None:
        pdf.saveState()
        pdf.setStrokeColor(LINE)
        pdf.setLineWidth(0.5)
        pdf.line(18 * mm, PAGE_HEIGHT - 12 * mm, PAGE_WIDTH - 18 * mm, PAGE_HEIGHT - 12 * mm)
        pdf.setFillColor(MUTED)
        pdf.setFont(font_name, 7)
        pdf.drawString(18 * mm, PAGE_HEIGHT - 9 * mm, f"{title} {metadata.get('version', '')}".strip())
        pdf.line(18 * mm, 12 * mm, PAGE_WIDTH - 18 * mm, 12 * mm)
        pdf.drawRightString(PAGE_WIDTH - 18 * mm, 7 * mm, f"第 {document.page + 1} 页")
        pdf.restoreState()

    toc: List[object] = [
        Paragraph("目录", styles["toc_title"]),
        Table(
            [[Paragraph(escape(item), styles["toc_item"])] for item in headings],
            colWidths=[170 * mm],
            style=TableStyle(
                [
                    ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#E0E8F2")),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ]
            ),
        ),
        PageBreak(),
    ]
    doc.build(toc + content, onFirstPage=header_footer, onLaterPages=header_footer)


def combine(cover: Path, body: Path, output: Path, metadata: Dict[str, str]) -> None:
    writer = PdfWriter()
    for source in [cover, body]:
        reader = PdfReader(str(source))
        for page in reader.pages:
            writer.add_page(page)
    writer.add_metadata(
        {
            "/Title": metadata.get("title", "正式方案"),
            "/Author": "Created with create-plan-skill",
            "/Subject": metadata.get("subtitle", ""),
        }
    )
    with output.open("wb") as file:
        writer.write(file)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a formal proposal Markdown file to a styled PDF."
    )
    parser.add_argument("proposal", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--font", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    proposal = args.proposal.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if not proposal.is_file():
        print(f"ERROR: proposal not found: {proposal}", file=sys.stderr)
        return 1
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        metadata, body = parse_frontmatter(proposal.read_text(encoding="utf-8"))
        font_path = find_font(args.font)
        pdfmetrics.registerFont(TTFont("PlanUnicode", str(font_path)))
        styles = load_styles("PlanUnicode")
        content, headings = parse_markdown(
            proposal,
            body,
            styles,
            "PlanUnicode",
        )
        cover = output.with_name(f".{output.stem}-cover.pdf")
        body_pdf = output.with_name(f".{output.stem}-body.pdf")
        make_cover(cover, metadata, "PlanUnicode")
        make_body(body_pdf, metadata, content, headings, styles, "PlanUnicode")
        combine(cover, body_pdf, output, metadata)
        cover.unlink(missing_ok=True)
        body_pdf.unlink(missing_ok=True)
        reader = PdfReader(str(output))
        digest = hashlib.sha256(output.read_bytes()).hexdigest()
    except (OSError, ValueError, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"pdf={output}")
    print(f"pages={len(reader.pages)}")
    print(f"sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
