#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

try:
    import yaml
except ImportError as error:
    print(
        "ERROR: Missing PyYAML. Install scripts/requirements-v2.txt.",
        file=sys.stderr,
    )
    raise SystemExit(2) from error


NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("SKILL.md must start with YAML frontmatter")
    try:
        closing = lines[1:].index("---") + 1
    except ValueError as error:
        raise ValueError("SKILL.md frontmatter is not closed") from error
    payload = yaml.safe_load("\n".join(lines[1:closing]))
    if not isinstance(payload, dict):
        raise ValueError("SKILL.md frontmatter must be a mapping")
    return payload


def validate(skill_dir: Path) -> list[str]:
    failures: list[str] = []
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file():
        return [f"missing SKILL.md: {skill_file}"]
    try:
        metadata = frontmatter(skill_file)
    except (OSError, ValueError, yaml.YAMLError) as error:
        return [str(error)]
    name = metadata.get("name")
    description = metadata.get("description")
    if not isinstance(name, str) or not NAME_PATTERN.fullmatch(name):
        failures.append(f"invalid skill name: {name!r}")
    elif name != skill_dir.name:
        failures.append(f"skill name {name!r} does not match directory {skill_dir.name!r}")
    if (
        not isinstance(description, str)
        or not description.startswith("Use when")
        or len(description) > 500
    ):
        failures.append("description must start with 'Use when' and be <= 500 characters")
    text = skill_file.read_text(encoding="utf-8")
    if "[TODO:" in text:
        failures.append("SKILL.md contains TODO placeholder")
    return failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a repository Skill layout.")
    parser.add_argument("skill_dir", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    skill_dir = args.skill_dir.expanduser().resolve()
    failures = validate(skill_dir)
    for failure in failures:
        print(f"FAIL {failure}")
    print(f"failures={len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
