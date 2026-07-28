#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError as error:
    print("ERROR: Missing Pillow. Install scripts/requirements.txt.", file=sys.stderr)
    raise SystemExit(2) from error


def create_contact_sheet(
    pages_dir: Path,
    output: Path,
    columns: int,
    thumb_width: int,
) -> tuple[int, tuple[int, int]]:
    page_paths = sorted(pages_dir.glob("page-*.png"))
    if not page_paths:
        raise RuntimeError(f"No page-*.png images found in {pages_dir}")
    margin = 24
    label_height = 30
    thumbnails: list[Image.Image] = []
    for path in page_paths:
        with Image.open(path) as image:
            converted = image.convert("RGB")
            height = max(1, round(converted.height * thumb_width / converted.width))
            thumbnails.append(converted.resize((thumb_width, height), Image.Resampling.LANCZOS))

    cell_height = max(image.height for image in thumbnails) + label_height
    rows = (len(thumbnails) + columns - 1) // columns
    width = margin + columns * (thumb_width + margin)
    height = margin + rows * (cell_height + margin)
    sheet = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()

    for index, image in enumerate(thumbnails):
        row, column = divmod(index, columns)
        x = margin + column * (thumb_width + margin)
        y = margin + row * (cell_height + margin)
        sheet.paste(image, (x, y))
        label = f"Page {index + 1}"
        draw.text((x, y + image.height + 8), label, fill="#23354D", font=font)

    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, format="PNG")
    return len(thumbnails), sheet.size


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a contact sheet from rendered PDF page PNGs."
    )
    parser.add_argument("pages_dir", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--columns", type=int, default=3)
    parser.add_argument("--thumb-width", type=int, default=420)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pages_dir = args.pages_dir.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if args.columns < 1 or args.columns > 8:
        print("ERROR: --columns must be between 1 and 8", file=sys.stderr)
        return 1
    if args.thumb_width < 160 or args.thumb_width > 1200:
        print("ERROR: --thumb-width must be between 160 and 1200", file=sys.stderr)
        return 1
    try:
        pages, size = create_contact_sheet(
            pages_dir,
            output,
            args.columns,
            args.thumb_width,
        )
    except (OSError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"contact_sheet={output}")
    print(f"pages={pages}")
    print(f"size={size[0]}x{size[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
