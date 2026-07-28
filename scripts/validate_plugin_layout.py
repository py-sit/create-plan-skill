#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

from validate_skill_layout import validate as validate_skill


SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


def validate(root: Path, strict_root_name: bool = False) -> list[str]:
    failures: list[str] = []
    manifest_path = root / ".codex-plugin" / "plugin.json"
    if not manifest_path.is_file():
        return [f"missing plugin manifest: {manifest_path}"]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"invalid plugin manifest: {error}"]
    required = ["name", "version", "description", "author", "skills", "interface"]
    for key in required:
        if key not in manifest:
            failures.append(f"missing plugin field: {key}")
    if strict_root_name and manifest.get("name") != root.name:
        failures.append(
            f"plugin name {manifest.get('name')!r} does not match directory {root.name!r}"
        )
    version = manifest.get("version")
    if not isinstance(version, str) or not SEMVER.fullmatch(version):
        failures.append(f"invalid plugin version: {version!r}")
    if "hooks" in manifest:
        failures.append("unsupported plugin field: hooks")
    skills_path = manifest.get("skills")
    if skills_path != "./skills/":
        failures.append(f"skills must be './skills/', got {skills_path!r}")
    interface = manifest.get("interface")
    if not isinstance(interface, dict):
        failures.append("interface must be an object")
    else:
        for key in ("displayName", "shortDescription", "longDescription", "developerName", "category"):
            if not isinstance(interface.get(key), str) or not interface[key].strip():
                failures.append(f"missing interface field: {key}")
    skills_dir = root / "skills"
    skill_files = sorted(skills_dir.glob("*/SKILL.md"))
    if not skill_files:
        failures.append("plugin contains no skills")
    for skill_file in skill_files:
        failures.extend(
            f"{skill_file.parent.name}: {failure}"
            for failure in validate_skill(skill_file.parent)
        )
    return failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the local Codex plugin layout.")
    parser.add_argument("plugin_root", type=Path)
    parser.add_argument("--strict-root-name", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.plugin_root.expanduser().resolve()
    failures = validate(root, args.strict_root_name)
    for failure in failures:
        print(f"FAIL {failure}")
    print(f"failures={len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
