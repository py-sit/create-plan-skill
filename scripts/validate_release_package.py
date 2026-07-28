#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = {
    ".codex-plugin/plugin.json",
    "README.md",
    "SKILL.md",
    "license.txt",
    "scripts/install_skills.py",
    "skills/create-plan-skill/SKILL.md",
    "skills/clarify-plan-requirements/SKILL.md",
    "skills/research-plan-options/SKILL.md",
    "skills/author-formal-plan/SKILL.md",
    "skills/validate-plan-package/SKILL.md",
}


def command_failure(command: list[str]) -> str:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return ""
    return (result.stdout + result.stderr).strip()


def validate(archive_path: Path) -> dict[str, object]:
    failures: list[str] = []
    version = ""
    if not archive_path.is_file():
        return {
            "archive": archive_path.name,
            "version": version,
            "failures": ["archive not found"],
        }
    try:
        with zipfile.ZipFile(archive_path) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                failures.append("archive contains duplicate entries")
            for name in names:
                path = PurePosixPath(name)
                if path.is_absolute() or ".." in path.parts:
                    failures.append(f"unsafe archive path: {name}")
            missing = sorted(REQUIRED_FILES - set(names))
            if missing:
                failures.append(f"missing required files: {missing}")
            with tempfile.TemporaryDirectory() as temporary:
                extracted = Path(temporary) / "create-plan-skill"
                extracted.mkdir()
                archive.extractall(extracted)
                manifest_path = extracted / ".codex-plugin" / "plugin.json"
                if manifest_path.is_file():
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    version = str(manifest.get("version", ""))
                plugin_error = command_failure(
                    [
                        sys.executable,
                        str(extracted / "scripts" / "validate_plugin_layout.py"),
                        str(extracted),
                        "--strict-root-name",
                    ]
                )
                if plugin_error:
                    failures.append(f"plugin validation failed: {plugin_error}")
                for skill_dir in sorted((extracted / "skills").glob("*")):
                    if not skill_dir.is_dir():
                        continue
                    skill_error = command_failure(
                        [
                            sys.executable,
                            str(extracted / "scripts" / "validate_skill_layout.py"),
                            str(skill_dir),
                        ]
                    )
                    if skill_error:
                        failures.append(
                            f"skill validation failed for {skill_dir.name}: {skill_error}"
                        )
                privacy_error = command_failure(
                    [
                        sys.executable,
                        str(extracted / "scripts" / "scan_sensitive_content.py"),
                        str(extracted),
                    ]
                )
                if privacy_error:
                    failures.append(f"privacy scan failed: {privacy_error}")
    except (OSError, ValueError, json.JSONDecodeError, zipfile.BadZipFile) as error:
        failures.append(str(error))
    return {
        "archive": archive_path.name,
        "version": version,
        "failures": failures,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a packaged create-plan-skill release ZIP."
    )
    parser.add_argument("archive", type=Path)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = validate(args.archive.expanduser().resolve())
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"archive={payload['archive']}")
        print(f"version={payload['version']}")
        for failure in payload["failures"]:
            print(f"FAIL {failure}")
        print(f"failures={len(payload['failures'])}")
    return 1 if payload["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
