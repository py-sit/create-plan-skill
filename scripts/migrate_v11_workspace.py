#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml
except ImportError as error:
    print(
        "ERROR: Missing PyYAML. Install scripts/requirements-v2.txt.",
        file=sys.stderr,
    )
    raise SystemExit(2) from error


SKILL_VERSION = "2.0.0"
REQUIRED_FILES = (
    "proposal.md",
    "brief.md",
    "evidence-register.md",
    "decision-log.md",
)
TARGET_FILES = (
    "plan-manifest.yaml",
    "source-register.yaml",
)
LANGUAGES = ("en-US", "zh-CN")
MODES = (
    "discovery-only",
    "research-and-options",
    "full-proposal",
    "validation-only",
)
THEME_PATTERN = re.compile(r"^[a-z0-9-]+$")
HEADING_PATTERN = re.compile(r"^#\s+(.+?)\s*$")
CJK_PATTERN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")


class MigrationError(ValueError):
    """Raised when a workspace cannot be migrated safely."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Safely add V2 metadata files to an existing V1.1 plan workspace. "
            "The default is a read-only dry run."
        )
    )
    parser.add_argument("workspace", type=Path)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create missing V2 metadata files. Without this flag, no files are written.",
    )
    parser.add_argument(
        "--theme",
        help="Theme identifier for plan-manifest.yaml (default: corporate-blue).",
    )
    parser.add_argument(
        "--mode",
        choices=MODES,
        help="Operating mode for plan-manifest.yaml (default: full-proposal).",
    )
    parser.add_argument(
        "--language",
        choices=LANGUAGES,
        help="Workspace language override. Otherwise inferred from existing Markdown.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print a machine-readable JSON result.",
    )
    return parser.parse_args()


def validate_workspace(workspace: Path) -> None:
    if not workspace.exists():
        raise MigrationError(f"Workspace does not exist: {workspace}")
    if not workspace.is_dir():
        raise MigrationError(f"Workspace is not a directory: {workspace}")

    missing = [
        name
        for name in REQUIRED_FILES
        if not (workspace / name).is_file()
    ]
    if missing:
        raise MigrationError(
            "Workspace is missing required V1.1 files: " + ", ".join(missing)
        )


def infer_title(proposal: Path, workspace: Path) -> str:
    for line in proposal.read_text(encoding="utf-8").splitlines():
        match = HEADING_PATTERN.match(line)
        if match:
            title = match.group(1).strip()
            if title:
                return title
    return workspace.name or "Formal Plan"


def infer_language(workspace: Path) -> str:
    sample = "\n".join(
        (workspace / name).read_text(encoding="utf-8")
        for name in ("proposal.md", "brief.md")
    )
    return "zh-CN" if CJK_PATTERN.search(sample) else "en-US"


def normalize_theme(value: Optional[str]) -> str:
    theme = (value or "corporate-blue").strip()
    if not theme or not THEME_PATTERN.fullmatch(theme):
        raise MigrationError(
            "Theme must contain only lowercase letters, digits, and hyphens."
        )
    return theme


def build_documents(
    workspace: Path,
    language: str,
    mode: str,
    theme: str,
) -> Dict[str, Dict[str, Any]]:
    manifest = {
        "schema_version": "2.0",
        "skill_version": SKILL_VERSION,
        "title": infer_title(workspace / "proposal.md", workspace),
        "language": language,
        "mode": mode,
        "stage": "discovery",
        "theme": theme,
        "render": {
            "engine": "playwright",
            "fallback": "reportlab",
            "visual_review": "pending",
        },
        "artifacts": {
            "brief": "brief.md",
            "questions": "questions.md",
            "evidence_register": "evidence-register.md",
            "source_register": "source-register.yaml",
            "decision_log": "decision-log.md",
            "proposal": "proposal.md",
            "diagrams": "diagrams",
            "pdf": "output/pdf/formal-plan.pdf",
            "rendered_pages": "tmp/rendered-pages",
        },
    }
    source_register = {
        "schema_version": "2.0",
        "sources": [],
    }
    return {
        "plan-manifest.yaml": manifest,
        "source-register.yaml": source_register,
    }


def serialize_document(document: Dict[str, Any]) -> str:
    return yaml.safe_dump(
        document,
        allow_unicode=True,
        sort_keys=False,
    )


def create_missing_files(
    workspace: Path,
    documents: Dict[str, Dict[str, Any]],
    apply: bool,
) -> Tuple[List[str], List[str], List[str]]:
    planned: List[str] = []
    created: List[str] = []
    skipped: List[str] = []

    for name in TARGET_FILES:
        path = workspace / name
        if path.exists():
            skipped.append(name)
        else:
            planned.append(name)

    if not apply:
        return planned, created, skipped

    for name in planned:
        path = workspace / name
        try:
            with path.open("x", encoding="utf-8") as output:
                output.write(serialize_document(documents[name]))
        except FileExistsError:
            skipped.append(name)
            continue
        created.append(name)

    return planned, created, skipped


def result_payload(
    workspace: Path,
    apply: bool,
    language: str,
    mode: str,
    theme: str,
    title: str,
    planned: List[str],
    created: List[str],
    skipped: List[str],
) -> Dict[str, Any]:
    if not apply:
        status = "dry-run"
    elif created:
        status = "applied"
    else:
        status = "skipped"
    return {
        "status": status,
        "workspace": str(workspace),
        "dry_run": not apply,
        "applied": apply,
        "settings": {
            "title": title,
            "language": language,
            "mode": mode,
            "theme": theme,
        },
        "required_files": list(REQUIRED_FILES),
        "planned": planned,
        "created": created,
        "skipped": skipped,
    }


def print_result(payload: Dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    print(f"workspace={payload['workspace']}")
    print(f"status={payload['status']}")
    print(f"dry_run={str(payload['dry_run']).lower()}")
    print(f"language={payload['settings']['language']}")
    print(f"mode={payload['settings']['mode']}")
    print(f"theme={payload['settings']['theme']}")
    print(f"planned={','.join(payload['planned']) or '-'}")
    print(f"created={','.join(payload['created']) or '-'}")
    print(f"skipped={','.join(payload['skipped']) or '-'}")


def print_error(
    error: Exception,
    workspace: Path,
    apply: bool,
    as_json: bool,
) -> None:
    if as_json:
        print(
            json.dumps(
                {
                    "status": "error",
                    "workspace": str(workspace),
                    "dry_run": not apply,
                    "applied": apply,
                    "created": [],
                    "skipped": [],
                    "error": str(error),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    print(f"ERROR: {error}", file=sys.stderr)


def main() -> int:
    args = parse_args()
    workspace = args.workspace.expanduser().resolve()

    try:
        validate_workspace(workspace)
        language = args.language or infer_language(workspace)
        mode = args.mode or "full-proposal"
        theme = normalize_theme(args.theme)
        documents = build_documents(
            workspace,
            language=language,
            mode=mode,
            theme=theme,
        )
        planned, created, skipped = create_missing_files(
            workspace,
            documents,
            apply=args.apply,
        )
        payload = result_payload(
            workspace,
            apply=args.apply,
            language=language,
            mode=mode,
            theme=theme,
            title=str(documents["plan-manifest.yaml"]["title"]),
            planned=planned,
            created=created,
            skipped=skipped,
        )
    except (MigrationError, OSError, UnicodeError, yaml.YAMLError) as error:
        print_error(error, workspace, args.apply, args.json)
        return 1

    print_result(payload, args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
