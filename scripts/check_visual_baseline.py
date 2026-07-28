#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

try:
    from PIL import Image
    import yaml
except ImportError as error:
    print(
        "ERROR: Missing V2 dependency. Install scripts/requirements-v2.txt.",
        file=sys.stderr,
    )
    raise SystemExit(2) from error


ROOT = Path(__file__).resolve().parents[1]
BASELINES = ROOT / "evals" / "visual-baselines.yaml"
PAGE_PATTERN = re.compile(r"^page-(\d+)\.png$")


def page_number(path: Path) -> int:
    match = PAGE_PATTERN.match(path.name)
    return int(match.group(1)) if match else sys.maxsize


def image_metrics(path: Path) -> dict[str, float | int]:
    with Image.open(path).convert("RGB") as image:
        sample = image.copy()
        sample.thumbnail((500, 700))
        pixels = list(sample.getdata())
        total = max(1, len(pixels))
        dark = sum(1 for red, green, blue in pixels if (red + green + blue) / 3 < 190)
        ink = sum(1 for red, green, blue in pixels if min(red, green, blue) < 245)
        return {
            "width": image.width,
            "height": image.height,
            "aspect_ratio": image.width / image.height,
            "dark_ratio": dark / total,
            "ink_ratio": ink / total,
        }


def in_range(value: float, boundary: dict[str, Any]) -> bool:
    return float(boundary["min"]) <= value <= float(boundary["max"])


def evaluate(pages_dir: Path, language: str) -> dict[str, Any]:
    baselines = yaml.safe_load(BASELINES.read_text(encoding="utf-8"))
    if language not in baselines:
        raise ValueError(f"Unknown language baseline: {language}")
    baseline = baselines[language]
    pages = sorted(
        (
            path
            for path in pages_dir.glob("page-*.png")
            if PAGE_PATTERN.match(path.name)
        ),
        key=page_number,
    )
    failures: list[str] = []
    metrics = [image_metrics(path) for path in pages]
    if len(pages) < int(baseline["min_pages"]):
        failures.append(
            f"page_count:{len(pages)}<{baseline['min_pages']}"
        )
    for index, page in enumerate(metrics, start=1):
        if not in_range(
            float(page["aspect_ratio"]),
            baseline["page_aspect_ratio"],
        ):
            failures.append(
                f"page_{index}_aspect_ratio:{page['aspect_ratio']:.4f}"
            )
        if not in_range(float(page["ink_ratio"]), baseline["page_ink_ratio"]):
            failures.append(f"page_{index}_ink_ratio:{page['ink_ratio']:.4f}")
    if metrics and not in_range(
        float(metrics[0]["dark_ratio"]),
        baseline["cover_dark_ratio"],
    ):
        failures.append(
            f"cover_dark_ratio:{metrics[0]['dark_ratio']:.4f}"
        )
    return {
        "baseline": baseline["name"],
        "language": language,
        "pages": len(pages),
        "metrics": metrics,
        "failures": failures,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check rendered PDF pages against the V2 visual baseline."
    )
    parser.add_argument("pages_dir", type=Path)
    parser.add_argument("--language", choices=["zh-CN", "en-US"], required=True)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pages_dir = args.pages_dir.expanduser().resolve()
    if not pages_dir.is_dir():
        print(f"ERROR: pages directory not found: {pages_dir}", file=sys.stderr)
        return 2
    try:
        payload = evaluate(pages_dir, args.language)
    except (OSError, ValueError, yaml.YAMLError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"baseline={payload['baseline']}")
        print(f"language={payload['language']}")
        print(f"pages={payload['pages']}")
        for failure in payload["failures"]:
            print(f"FAIL {failure}")
        print(f"failures={len(payload['failures'])}")
    return 1 if payload["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
