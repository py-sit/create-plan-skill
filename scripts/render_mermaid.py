#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request


FORMATS = ("svg", "png", "pdf")


def validate_artifact(path: Path, file_format: str) -> None:
    if not path.exists() or path.stat().st_size < 100:
        raise RuntimeError(f"Renderer produced an empty artifact: {path}")
    head = path.read_bytes()[:512]
    if file_format == "pdf" and not head.startswith(b"%PDF"):
        raise RuntimeError(f"Invalid PDF output: {path}")
    if file_format == "png" and not head.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError(f"Invalid PNG output: {path}")
    if file_format == "svg" and b"<svg" not in head.lower():
        raise RuntimeError(f"Invalid SVG output: {path}")


def render_with_mmdc(source: Path, destination: Path) -> None:
    executable = shutil.which("mmdc")
    if not executable:
        raise RuntimeError("mmdc is not installed")
    command = [
        executable,
        "-i",
        str(source),
        "-o",
        str(destination),
        "-b",
        "transparent",
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"mmdc failed for {destination.suffix}: {details}")


def render_with_kroki(
    source_text: str,
    destination: Path,
    file_format: str,
    endpoint: str,
    timeout: int,
    attempts: int = 3,
) -> None:
    url = f"{endpoint.rstrip('/')}/mermaid/{file_format}"
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        request = urllib.request.Request(
            url,
            data=source_text.encode("utf-8"),
            headers={
                "Content-Type": "text/plain; charset=utf-8",
                "User-Agent": "create-plan-skill/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                if response.status != 200:
                    raise RuntimeError(f"Kroki returned HTTP {response.status}")
                destination.write_bytes(response.read())
                return
        except urllib.error.HTTPError as error:
            details = error.read().decode("utf-8", errors="replace").strip()
            if 400 <= error.code < 500 and error.code != 429:
                raise RuntimeError(
                    f"Kroki rejected the Mermaid source: HTTP {error.code}: {details}"
                ) from error
            last_error = error
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            last_error = error
        if attempt < attempts:
            time.sleep(attempt)
    raise RuntimeError(f"Kroki request failed after {attempts} attempts: {last_error}")


def chrome_candidates() -> list[str]:
    values = [
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ]
    return [value for value in values if value and Path(value).is_file()]


def svg_dimensions(source: Path) -> tuple[float, float]:
    head = source.read_text(encoding="utf-8")[:2048]
    width_match = re.search(r'\bwidth="([0-9.]+)', head)
    height_match = re.search(r'\bheight="([0-9.]+)', head)
    if width_match and height_match:
        return float(width_match.group(1)), float(height_match.group(1))
    view_box = re.search(
        r'\bviewBox="[0-9.+-]+\s+[0-9.+-]+\s+([0-9.]+)\s+([0-9.]+)"',
        head,
    )
    if view_box:
        return float(view_box.group(1)), float(view_box.group(2))
    return 1200.0, 800.0


def crop_png(path: Path, margin: int = 24) -> None:
    from PIL import Image, ImageChops

    with Image.open(path).convert("RGBA") as image:
        background = Image.new("RGBA", image.size, image.getpixel((0, 0)))
        difference = ImageChops.difference(image, background)
        bbox = difference.getbbox()
        if not bbox:
            return
        left = max(0, bbox[0] - margin)
        top = max(0, bbox[1] - margin)
        right = min(image.width, bbox[2] + margin)
        bottom = min(image.height, bbox[3] + margin)
        image.crop((left, top, right, bottom)).save(path, format="PNG")


def convert_svg_to_png(source: Path, destination: Path) -> str:
    try:
        import cairosvg  # type: ignore[import-not-found]

        cairosvg.svg2png(url=str(source), write_to=str(destination), output_width=1800)
        return "cairosvg"
    except (ImportError, OSError):
        pass

    rsvg = shutil.which("rsvg-convert")
    if rsvg:
        result = subprocess.run(
            [rsvg, "-f", "png", "-w", "1800", "-o", str(destination), str(source)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return "rsvg-convert"

    inkscape = shutil.which("inkscape")
    if inkscape:
        result = subprocess.run(
            [
                inkscape,
                str(source),
                "--export-type=png",
                "--export-width=1800",
                f"--export-filename={destination}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return "inkscape"

    source_width, source_height = svg_dimensions(source)
    scale = min(1800.0 / max(source_width, source_height), 4.0)
    viewport_width = max(500, int(round(source_width * scale)))
    viewport_height = max(500, int(round(source_height * scale)))
    for candidate in chrome_candidates():
        result = subprocess.run(
            [
                candidate,
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                f"--window-size={viewport_width},{viewport_height}",
                f"--screenshot={destination}",
                source.as_uri(),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and destination.is_file():
            crop_png(destination)
            return "chrome"

    raise RuntimeError(
        "Cannot convert Mermaid SVG to PNG. Install CairoSVG, rsvg-convert, "
        "Inkscape, or Chrome/Chromium."
    )


def convert_svg_to_pdf(
    source: Path,
    destination: Path,
    png_fallback: Path,
) -> str:
    try:
        import cairosvg  # type: ignore[import-not-found]

        cairosvg.svg2pdf(url=str(source), write_to=str(destination))
        return "cairosvg"
    except (ImportError, OSError):
        pass

    rsvg = shutil.which("rsvg-convert")
    if rsvg:
        result = subprocess.run(
            [rsvg, "-f", "pdf", "-o", str(destination), str(source)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return "rsvg-convert"

    inkscape = shutil.which("inkscape")
    if inkscape:
        result = subprocess.run(
            [
                inkscape,
                str(source),
                "--export-type=pdf",
                f"--export-filename={destination}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return "inkscape"

    try:
        from PIL import Image

        with Image.open(png_fallback).convert("RGB") as image:
            image.save(destination, format="PDF", resolution=180.0)
        return "pillow"
    except (ImportError, OSError) as error:
        raise RuntimeError(f"PNG-to-PDF fallback failed: {error}") from error


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render Mermaid source to SVG, PNG, and PDF."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument(
        "--engine",
        choices=("auto", "mmdc", "kroki"),
        default="auto",
    )
    parser.add_argument(
        "--allow-network",
        action="store_true",
        help="Allow sending non-sensitive Mermaid source to a public Kroki endpoint.",
    )
    parser.add_argument("--kroki-endpoint", default="https://kroki.io")
    parser.add_argument("--timeout", type=int, default=60)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source.expanduser().resolve()
    if not source.is_file():
        print(f"ERROR: Mermaid source not found: {source}", file=sys.stderr)
        return 1
    source_text = source.read_text(encoding="utf-8")
    if not source_text.strip():
        print("ERROR: Mermaid source is empty", file=sys.stderr)
        return 1

    out_dir = args.out_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    has_mmdc = shutil.which("mmdc") is not None

    if args.engine == "mmdc" and not has_mmdc:
        print("ERROR: mmdc is not installed", file=sys.stderr)
        return 1
    if args.engine == "kroki" and not args.allow_network:
        print(
            "ERROR: --engine kroki requires --allow-network. "
            "Do not upload sensitive diagrams.",
            file=sys.stderr,
        )
        return 1
    if args.engine == "auto" and not has_mmdc and not args.allow_network:
        print(
            "ERROR: no local mmdc found. Install Mermaid CLI or rerun with "
            "--allow-network for non-sensitive diagrams.",
            file=sys.stderr,
        )
        return 1

    try:
        use_mmdc = args.engine == "mmdc" or (args.engine == "auto" and has_mmdc)
        if use_mmdc:
            for file_format in FORMATS:
                destination = out_dir / f"{source.stem}.{file_format}"
                render_with_mmdc(source, destination)
                engine = "mmdc"
                validate_artifact(destination, file_format)
                print(f"{file_format}={destination}")
        else:
            svg_destination = out_dir / f"{source.stem}.svg"
            render_with_kroki(
                source_text,
                svg_destination,
                "svg",
                args.kroki_endpoint,
                args.timeout,
            )
            engine = "kroki"
            validate_artifact(svg_destination, "svg")
            print(f"svg={svg_destination}")
            png_destination = out_dir / f"{source.stem}.png"
            png_converter = convert_svg_to_png(svg_destination, png_destination)
            validate_artifact(png_destination, "png")
            print(f"png={png_destination}")
            print(f"png_converter={png_converter}")
            pdf_destination = out_dir / f"{source.stem}.pdf"
            converter = convert_svg_to_pdf(
                svg_destination,
                pdf_destination,
                png_destination,
            )
            validate_artifact(pdf_destination, "pdf")
            print(f"pdf={pdf_destination}")
            print(f"pdf_converter={converter}")
        print(f"engine={engine}")
    except (OSError, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
