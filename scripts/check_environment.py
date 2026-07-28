#!/usr/bin/env python3
from __future__ import annotations

import argparse
from importlib import metadata
import json
from pathlib import Path
import platform
import shutil
import sys
from typing import Dict


SKILL_ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = SKILL_ROOT / "scripts" / "requirements.txt"

FONT_CANDIDATES = [
    Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttf"),
    Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttf"),
    Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttf"),
]

CHROME_CANDIDATES = [
    Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
]


def first_command(*names: str) -> str:
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    return ""


def expected_package_versions() -> Dict[str, str]:
    result: Dict[str, str] = {}
    for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "==" not in stripped:
            continue
        name, version = stripped.split("==", 1)
        result[name.strip()] = version.strip()
    return result


def package_versions() -> Dict[str, Dict[str, object]]:
    result: Dict[str, Dict[str, object]] = {}
    for distribution, expected in expected_package_versions().items():
        try:
            version = metadata.version(distribution)
            matches = version == expected
            result[distribution] = {
                "status": "ready" if matches else "version-mismatch",
                "version": version,
                "expected": expected,
                "matches_pin": matches,
            }
        except metadata.PackageNotFoundError:
            result[distribution] = {
                "status": "missing",
                "version": "",
                "expected": expected,
                "matches_pin": False,
            }
    return result


def find_font() -> str:
    for candidate in FONT_CANDIDATES:
        if candidate.is_file():
            return str(candidate)
    return ""


def find_chrome() -> str:
    command = first_command("google-chrome", "chromium", "chromium-browser")
    if command:
        return command
    for candidate in CHROME_CANDIDATES:
        if candidate.is_file():
            return str(candidate)
    return ""


def collect_capabilities() -> Dict[str, object]:
    python_ready = sys.version_info >= (3, 9)
    packages = package_versions()
    mmdc = first_command("mmdc")
    svg_converter = (
        first_command("rsvg-convert", "inkscape")
        or find_chrome()
    )
    pdftoppm = first_command("pdftoppm")
    font = find_font()
    return {
        "python": {
            "status": "ready" if python_ready else "unsupported",
            "version": platform.python_version(),
            "minimum": "3.9",
            "executable": sys.executable,
            "architecture": platform.machine(),
        },
        "python_packages": packages,
        "mermaid": {
            "status": "ready" if mmdc else "network-permission-required",
            "mmdc": mmdc,
            "public_fallback": "Kroki requires explicit --allow-network",
            "svg_converter": svg_converter,
        },
        "pdf_pages": {
            "status": "ready" if pdftoppm else "missing",
            "pdftoppm": pdftoppm,
        },
        "font": {
            "status": "ready" if font else "missing",
            "path": font,
        },
    }


def strict_failures(payload: Dict[str, object]) -> list[str]:
    failures: list[str] = []
    python = payload["python"]
    if isinstance(python, dict) and python.get("status") != "ready":
        failures.append("python")
    packages = payload["python_packages"]
    if isinstance(packages, dict):
        failures.extend(
            f"package:{name}"
            for name, details in packages.items()
            if isinstance(details, dict) and details.get("status") != "ready"
        )
    for key in ("pdf_pages", "font"):
        details = payload[key]
        if isinstance(details, dict) and details.get("status") != "ready":
            failures.append(key)
    return failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check create-plan-skill runtime and rendering capabilities."
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero when required local PDF capabilities are missing.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = collect_capabilities()
    failures = strict_failures(payload)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for section, value in payload.items():
            print(f"{section}={json.dumps(value, ensure_ascii=False)}")
        print(f"strict_failures={len(failures)}")
    return 1 if args.strict and failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
