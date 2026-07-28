#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import re
import shutil
import sys


SKILL_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = SKILL_ROOT / "assets" / "formal-plan-template.md"


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value)
    return value.strip("-") or "formal-plan"


def write_text(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"Refusing to overwrite existing file: {path}")
    path.write_text(content, encoding="utf-8")


def build_workspace(output_dir: Path, title: str, force: bool) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for directory in [
        output_dir / "assets",
        output_dir / "diagrams",
        output_dir / "diagrams" / "rendered",
        output_dir / "output" / "pdf",
        output_dir / "tmp" / "rendered-pages",
    ]:
        directory.mkdir(parents=True, exist_ok=True)

    proposal = TEMPLATE.read_text(encoding="utf-8")
    proposal = proposal.replace("<方案名称>", title)
    proposal = proposal.replace("<YYYY-MM-DD>", date.today().isoformat())
    write_text(output_dir / "proposal.md", proposal, force)

    write_text(
        output_dir / "brief.md",
        f"""# {title} - Confirmed Brief

## Outcome

## Audience

## Current problem

## Trigger and workflow

## Required inputs

## Required outputs

## Authority boundary

## Privacy and security boundary

## Acceptance criteria

## Non-goals
""",
        force,
    )
    write_text(
        output_dir / "questions.md",
        """# Discovery Questions

| ID | Question | Why it matters | Answer | Status |
| --- | --- | --- | --- | --- |
| Q-001 |  |  |  | open |
""",
        force,
    )
    write_text(
        output_dir / "evidence-register.md",
        """# Evidence Register

| ID | Claim | Label | Source | Freshness | Impact |
| --- | --- | --- | --- | --- | --- |
| E-001 |  |  |  |  |  |
""",
        force,
    )
    write_text(
        output_dir / "decision-log.md",
        """# Decision Log

## D-001

- **Decision**:
- **Status**: proposed
- **Context**:
- **Options considered**:
- **Selected option**:
- **Why**:
- **Trade-offs**:
- **Failure boundary**:
- **Rollback or exit strategy**:
- **Validation needed**:
""",
        force,
    )
    write_text(
        output_dir / "diagrams" / "architecture.mmd",
        """flowchart LR
    A["用户操作"] --> B["业务服务"]
    B --> C["数据与任务"]
    C --> D["处理组件"]
    D --> E["正式交付物"]
""",
        force,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a clean workspace for a formal proposal."
    )
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite scaffold files if they already exist.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        build_workspace(args.output_dir.expanduser().resolve(), args.title, args.force)
    except (FileExistsError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    output_dir = args.output_dir.expanduser().resolve()
    print(f"workspace={output_dir}")
    print(f"proposal={output_dir / 'proposal.md'}")
    print(f"slug={slugify(args.title)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
