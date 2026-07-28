#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Iterable, Pattern


DEFAULT_EXCLUDES = {
    ".git",
    ".worktrees",
    ".venv",
    "__pycache__",
    "dist",
    "node_modules",
    "output",
    "tmp",
}
RELEASE_ROOTS = {
    ".codex-plugin",
    "SKILL.md",
    "agents",
    "assets",
    "license.txt",
    "references",
    "scripts",
    "shared",
    "skills",
}
TEXT_SUFFIXES = {
    "",
    ".css",
    ".html",
    ".json",
    ".jsonl",
    ".md",
    ".mmd",
    ".py",
    ".txt",
    ".yaml",
    ".yml",
}


def compiled_rules() -> list[tuple[str, Pattern[str]]]:
    private_key = "-----BEGIN " + r"(?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
    return [
        ("private-key", re.compile(private_key)),
        ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,255}\b")),
        ("openai-token", re.compile(r"\bsk-[A-Za-z0-9_-]{20,255}\b")),
        ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
        (
            "jwt",
            re.compile(
                r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\."
                r"[A-Za-z0-9_-]{10,}\b"
            ),
        ),
        (
            "local-absolute-path",
            re.compile(
                r"(?<![A-Za-z0-9_.-])(?:/Users|/home)/"
                r"[A-Za-z0-9._-]+(?:/[^\s\"'`<>]*)?"
            ),
        ),
    ]


def is_excluded(relative: Path, excludes: set[str]) -> bool:
    return any(part in excludes for part in relative.parts)


def release_candidate(relative: Path) -> bool:
    return bool(relative.parts) and relative.parts[0] in RELEASE_ROOTS


def iter_text_files(
    root: Path,
    excludes: set[str],
    profile: str,
) -> Iterable[Path]:
    if root.is_file():
        candidates = [root]
        base = root.parent
    else:
        candidates = root.rglob("*")
        base = root
    for path in candidates:
        if not path.is_file() or path.is_symlink():
            continue
        try:
            relative = path.relative_to(base)
        except ValueError:
            continue
        if is_excluded(relative, excludes):
            continue
        if profile == "release" and not release_candidate(relative):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if path.stat().st_size > 2_000_000:
            continue
        yield path


def scan(
    root: Path,
    excludes: set[str],
    profile: str,
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    base = root if root.is_dir() else root.parent
    rules = compiled_rules()
    for path in iter_text_files(root, excludes, profile):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            for rule_name, pattern in rules:
                for match in pattern.finditer(line):
                    matched = match.group(0)
                    findings.append(
                        {
                            "file": str(path.relative_to(base)),
                            "line": line_number,
                            "rule": rule_name,
                            "match_sha256": hashlib.sha256(
                                matched.encode("utf-8")
                            ).hexdigest(),
                        }
                    )
    return findings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Scan text files for high-confidence secrets and private local paths "
            "without echoing matched values."
        )
    )
    parser.add_argument("path", type=Path)
    parser.add_argument(
        "--profile",
        choices=["all", "release"],
        default="all",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Directory or path component to exclude. Repeatable.",
    )
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.path.expanduser().resolve()
    if not root.exists():
        print(f"ERROR: scan path not found: {root}", file=sys.stderr)
        return 2
    excludes = DEFAULT_EXCLUDES | set(args.exclude)
    findings = scan(root, excludes, args.profile)
    payload = {
        "path": root.name,
        "profile": args.profile,
        "findings": findings,
        "failures": len(findings),
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for finding in findings:
            print(
                "FAIL "
                f"{finding['rule']}:{finding['file']}:{finding['line']} "
                f"match_sha256={finding['match_sha256']}"
            )
        print(f"failures={len(findings)}")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
