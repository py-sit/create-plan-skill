#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / ".codex-plugin" / "plugin.json"
PACKAGE_ENTRIES = (
    ".codex-plugin",
    "SKILL.md",
    "README.md",
    "agents",
    "assets",
    "evals",
    "license.txt",
    "references",
    "scripts",
    "shared",
    "skills",
)
SKIPPED_PARTS = {
    "__pycache__",
    "dist",
    "output",
    "tmp",
}
SKIPPED_SUFFIXES = {
    ".pyc",
    ".pyo",
}
FIXED_TIMESTAMP = (2020, 1, 1, 0, 0, 0)


def plugin_version() -> str:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    version = payload.get("version")
    if not isinstance(version, str) or not version:
        raise ValueError("plugin.json has no version")
    return version


def package_files() -> list[Path]:
    files: list[Path] = []
    for entry in PACKAGE_ENTRIES:
        path = ROOT / entry
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(item for item in path.rglob("*") if item.is_file())
        else:
            raise FileNotFoundError(f"Package entry not found: {path}")
    return sorted(
        (
            path
            for path in files
            if not any(part in SKIPPED_PARTS for part in path.relative_to(ROOT).parts)
            and path.suffix.lower() not in SKIPPED_SUFFIXES
        ),
        key=lambda path: path.relative_to(ROOT).as_posix(),
    )


def write_archive(output: Path) -> str:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    with zipfile.ZipFile(
        temporary,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for source in package_files():
            relative = source.relative_to(ROOT).as_posix()
            info = zipfile.ZipInfo(relative, FIXED_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            mode = 0o755 if source.suffix == ".py" else 0o644
            info.external_attr = (mode & 0xFFFF) << 16
            archive.writestr(info, source.read_bytes(), compresslevel=9)
    temporary.replace(output)
    return hashlib.sha256(output.read_bytes()).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a deterministic create-plan-skill plugin ZIP."
    )
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        version = plugin_version()
        output_dir = args.output_dir.expanduser().resolve()
        archive = output_dir / f"create-plan-skill-{version}.zip"
        digest = write_archive(archive)
        checksum = archive.with_suffix(archive.suffix + ".sha256")
        checksum.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    except (OSError, ValueError, json.JSONDecodeError, zipfile.BadZipFile) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"archive={archive}")
    print(f"sha256_file={checksum}")
    print(f"sha256={digest}")
    print(f"version={version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
