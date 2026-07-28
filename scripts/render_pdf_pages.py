#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys

try:
    from pypdf import PdfReader
except ImportError as error:
    print("ERROR: Missing pypdf. Install scripts/requirements.txt.", file=sys.stderr)
    raise SystemExit(2) from error


def render_pages(pdf: Path, output_dir: Path, dpi: int) -> list[Path]:
    executable = shutil.which("pdftoppm")
    if not executable:
        raise RuntimeError("pdftoppm is required to render PDF pages")
    expected_pages = len(PdfReader(str(pdf)).pages)
    output_dir.mkdir(parents=True, exist_ok=True)
    for stale in output_dir.glob("page-*.png"):
        stale.unlink()

    prefix = output_dir / ".page"
    result = subprocess.run(
        [
            executable,
            "-png",
            "-r",
            str(dpi),
            str(pdf),
            str(prefix),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"pdftoppm failed: {details}")

    generated = sorted(output_dir.glob(".page-*.png"))
    if len(generated) != expected_pages:
        raise RuntimeError(
            f"Rendered page count mismatch: generated={len(generated)} "
            f"expected={expected_pages}"
        )
    final_paths: list[Path] = []
    width = max(3, len(str(expected_pages)))
    for index, source in enumerate(generated, start=1):
        destination = output_dir / f"page-{index:0{width}d}.png"
        source.replace(destination)
        final_paths.append(destination)
    return final_paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render every PDF page to PNG.")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--dpi", type=int, default=140)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pdf = args.pdf.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    if not pdf.is_file():
        print(f"ERROR: PDF not found: {pdf}", file=sys.stderr)
        return 1
    if args.dpi < 72 or args.dpi > 300:
        print("ERROR: --dpi must be between 72 and 300", file=sys.stderr)
        return 1
    try:
        pages = render_pages(pdf, output_dir, args.dpi)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"pdf={pdf}")
    print(f"output_dir={output_dir}")
    print(f"pages={len(pages)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
