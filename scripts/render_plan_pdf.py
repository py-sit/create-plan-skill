#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


SCRIPT_ROOT = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Render a formal proposal to PDF. The V1-compatible default remains "
            "ReportLab; V2 plugin workflows select Playwright explicitly."
        )
    )
    parser.add_argument("proposal", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--font", type=Path)
    parser.add_argument(
        "--engine",
        choices=["reportlab", "playwright", "auto"],
        default="reportlab",
    )
    parser.add_argument("--theme")
    parser.add_argument("--html-output", type=Path)
    parser.add_argument("--browser-executable", type=Path)
    return parser.parse_args()


def render_reportlab(args: argparse.Namespace, fallback: str = "") -> int:
    command = [
        sys.executable,
        str(SCRIPT_ROOT / "render_plan_pdf_reportlab.py"),
        str(args.proposal),
        "--output",
        str(args.output),
    ]
    if args.font:
        command.extend(["--font", str(args.font)])
    result = subprocess.run(command, check=False)
    if result.returncode == 0:
        print("engine=reportlab")
        if fallback:
            print(f"fallback={fallback}")
    return result.returncode


def render_playwright(args: argparse.Namespace) -> int:
    from render_plan_pdf_playwright import RendererUnavailable, render

    try:
        result = render(
            proposal=args.proposal.expanduser().resolve(),
            output=args.output.expanduser().resolve(),
            theme=args.theme,
            html_output=(
                args.html_output.expanduser().resolve()
                if args.html_output
                else None
            ),
            browser_executable=(
                args.browser_executable.expanduser().resolve()
                if args.browser_executable
                else None
            ),
        )
    except RendererUnavailable as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    except (OSError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"pdf={result.pdf}")
    print(f"html={result.html}")
    print(f"pages={result.pages}")
    print(f"sha256={result.sha256}")
    print("engine=playwright")
    print(f"theme={result.theme}")
    return 0


def main() -> int:
    args = parse_args()
    if args.engine == "reportlab":
        return render_reportlab(args)
    if args.engine == "playwright":
        return render_playwright(args)

    playwright_result = render_playwright(args)
    if playwright_result == 2:
        print(
            "WARNING: Playwright is unavailable; using the explicit ReportLab "
            "compatibility fallback.",
            file=sys.stderr,
        )
        return render_reportlab(args, fallback="playwright-unavailable")
    return playwright_result


if __name__ == "__main__":
    raise SystemExit(main())
