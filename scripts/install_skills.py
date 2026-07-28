#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = ROOT / "skills"
SKILL_NAMES = (
    "create-plan-skill",
    "clarify-plan-requirements",
    "research-plan-options",
    "author-formal-plan",
    "validate-plan-package",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Install the five V2 skills by copying them into Codex and Agents "
            "skill directories. The default is a dry run."
        )
    )
    parser.add_argument(
        "--codex-root",
        type=Path,
        default=Path.home() / ".codex" / "skills",
    )
    parser.add_argument(
        "--agents-root",
        type=Path,
        default=Path.home() / ".agents" / "skills",
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--upgrade",
        action="store_true",
        help="Back up and replace existing skill directories.",
    )
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def remove_destination(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    else:
        shutil.rmtree(path)


def backup_destination(path: Path, backup: Path) -> None:
    backup.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        source = path.resolve()
        if source.is_dir():
            shutil.copytree(source, backup)
        else:
            shutil.copy2(source, backup)
    elif path.is_dir():
        shutil.copytree(path, backup)
    else:
        shutil.copy2(path, backup)


def install(
    codex_root: Path,
    agents_root: Path,
    apply: bool,
    upgrade: bool,
) -> dict[str, Any]:
    targets = [codex_root, agents_root]
    planned: list[str] = []
    installed: list[str] = []
    backed_up: list[str] = []
    conflicts: list[str] = []
    for target_root in targets:
        for name in SKILL_NAMES:
            destination = target_root / name
            planned.append(str(destination))
            if destination.exists() or destination.is_symlink():
                conflicts.append(str(destination))
    if conflicts and not upgrade and apply:
        return {
            "dry_run": not apply,
            "upgrade": upgrade,
            "planned": planned,
            "installed": installed,
            "backed_up": backed_up,
            "conflicts": conflicts,
            "error": "Existing skills require --upgrade.",
        }
    if not apply:
        return {
            "dry_run": True,
            "upgrade": upgrade,
            "planned": planned,
            "installed": installed,
            "backed_up": backed_up,
            "conflicts": conflicts,
            "error": "",
        }

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for target_root in targets:
        target_root.mkdir(parents=True, exist_ok=True)
        for name in SKILL_NAMES:
            source = SKILLS_ROOT / name
            destination = target_root / name
            if not source.is_dir():
                raise FileNotFoundError(f"Skill source not found: {source}")
            if destination.exists() or destination.is_symlink():
                backup = (
                    target_root
                    / ".create-plan-backups"
                    / stamp
                    / name
                )
                backup_destination(destination, backup)
                backed_up.append(str(backup))
                remove_destination(destination)
            shutil.copytree(source, destination)
            installed.append(str(destination))
    return {
        "dry_run": False,
        "upgrade": upgrade,
        "planned": planned,
        "installed": installed,
        "backed_up": backed_up,
        "conflicts": conflicts,
        "error": "",
    }


def main() -> int:
    args = parse_args()
    try:
        payload = install(
            args.codex_root.expanduser().resolve(),
            args.agents_root.expanduser().resolve(),
            args.apply,
            args.upgrade,
        )
    except OSError as error:
        payload = {
            "dry_run": not args.apply,
            "upgrade": args.upgrade,
            "planned": [],
            "installed": [],
            "backed_up": [],
            "conflicts": [],
            "error": str(error),
        }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"dry_run={str(payload['dry_run']).lower()}")
        print(f"upgrade={str(payload['upgrade']).lower()}")
        for path in payload["installed"]:
            print(f"installed={path}")
        for path in payload["backed_up"]:
            print(f"backup={path}")
        for path in payload["conflicts"]:
            print(f"conflict={path}")
        if payload["error"]:
            print(f"ERROR: {payload['error']}", file=sys.stderr)
    return 1 if payload["error"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
