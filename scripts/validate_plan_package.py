#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, Iterable, List, Sequence
from urllib.parse import unquote, urlparse

try:
    from pypdf import PdfReader
except ImportError as error:
    print("ERROR: Missing pypdf. Install scripts/requirements.txt.", file=sys.stderr)
    raise SystemExit(2) from error

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


MODES = (
    "discovery-only",
    "research-and-options",
    "full-proposal",
    "validation-only",
)

PLACEHOLDER_PATTERNS = [
    r"\bTODO\b",
    r"\bTBD\b",
    r"\bFIXME\b",
    r"<[^>\n]{2,80}>",
    r"\[待补充\]",
    r"\[占位\]",
]

SECTION_GROUPS = {
    "executive_summary": [r"执行摘要", r"Executive Summary"],
    "requirements": [r"需求", r"Requirements"],
    "alternatives": [r"方案选型", r"方案对比", r"Option Comparison", r"Alternatives"],
    "architecture": [r"架构", r"Architecture"],
    "security": [r"安全", r"隐私", r"Security", r"Privacy"],
    "acceptance": [r"验收", r"Acceptance"],
    "risks": [r"风险", r"Risks?"],
    "recommendation": [r"最终建议", r"Final Recommendation", r"Recommendation"],
}

RESEARCH_SECTIONS = ("requirements", "alternatives", "recommendation")
FULL_SECTIONS = tuple(SECTION_GROUPS)


def add_result(
    results: List[Dict[str, str]],
    check: str,
    passed: bool,
    details: str,
) -> None:
    results.append(
        {
            "status": "PASS" if passed else "FAIL",
            "check": check,
            "details": details,
        }
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_placeholders(
    label: str,
    text: str,
    results: List[Dict[str, str]],
) -> None:
    for pattern in PLACEHOLDER_PATTERNS:
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        add_result(
            results,
            f"{label}:placeholder:{pattern}",
            not matches,
            f"matches={matches[:5]}",
        )


def require_text_file(
    path: Path,
    label: str,
    results: List[Dict[str, str]],
) -> str:
    if not path.is_file():
        add_result(results, f"{label}_exists", False, str(path))
        return ""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        add_result(results, f"{label}_readable", False, str(error))
        return ""
    add_result(results, f"{label}_exists", True, str(path))
    validate_placeholders(label, text, results)
    return text


def validate_brief(path: Path, results: List[Dict[str, str]]) -> str:
    text = require_text_file(path, "brief", results)
    if not text:
        return text
    headings = re.findall(r"^##\s+(.+)$", text, flags=re.MULTILINE)
    normalized = "\n".join(headings)
    required = {
        "outcome": [r"Outcome", r"目标结果", r"目标"],
        "audience": [r"Audience", r"受众"],
        "problem": [r"Current problem", r"当前问题"],
        "acceptance": [r"Acceptance criteria", r"验收标准"],
    }
    for group, patterns in required.items():
        found = any(re.search(pattern, normalized, re.IGNORECASE) for pattern in patterns)
        add_result(results, f"brief_section:{group}", found, ", ".join(patterns))
    body_without_headings = re.sub(r"^#+\s+.*$", "", text, flags=re.MULTILINE)
    add_result(
        results,
        "brief_substantive_content",
        len(body_without_headings.strip()) >= 30,
        f"characters={len(body_without_headings.strip())}",
    )
    return text


def validate_evidence_register(path: Path, results: List[Dict[str, str]]) -> set[str]:
    text = require_text_file(path, "evidence_register", results)
    if not text:
        return set()
    evidence_ids = set(re.findall(r"(?m)^\|\s*(E-\d+)\s*\|", text))
    populated_rows = [
        line
        for line in text.splitlines()
        if re.match(r"^\|\s*E-\d+\s*\|", line)
        and len([cell for cell in line.strip().strip("|").split("|") if cell.strip()]) >= 5
    ]
    add_result(
        results,
        "evidence_rows",
        bool(populated_rows),
        f"ids={sorted(evidence_ids)}",
    )
    return evidence_ids


def read_evidence_ids(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return set()
    return set(re.findall(r"(?m)^\|\s*(E-\d+)\s*\|", text))


def read_yaml_mapping(
    path: Path,
    label: str,
    results: List[Dict[str, str]],
) -> Dict[str, Any] | None:
    if not path.is_file():
        add_result(results, f"{label}_exists", False, str(path))
        return None
    add_result(results, f"{label}_exists", True, str(path))
    if yaml is None:
        add_result(
            results,
            f"{label}_yaml_readable",
            False,
            "PyYAML missing; install scripts/requirements-v2.txt",
        )
        return None
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        add_result(results, f"{label}_yaml_readable", False, str(error))
        return None
    is_mapping = isinstance(loaded, dict)
    add_result(
        results,
        f"{label}_yaml_readable",
        is_mapping,
        "mapping" if is_mapping else f"expected mapping, got {type(loaded).__name__}",
    )
    return loaded if is_mapping else None


def validate_schema_version(
    document: Dict[str, Any] | None,
    label: str,
    results: List[Dict[str, str]],
) -> None:
    actual = document.get("schema_version") if document is not None else None
    add_result(
        results,
        f"{label}_schema_version",
        actual == "2.0",
        f"expected=2.0 actual={actual!r}",
    )


def validate_source_register(
    workspace: Path,
    document: Dict[str, Any] | None,
    evidence_ids: set[str],
    proposal_path: Path,
    results: List[Dict[str, str]],
) -> None:
    raw_sources = document.get("sources") if document is not None else None
    sources_are_list = isinstance(raw_sources, list)
    add_result(
        results,
        "source_register_sources",
        sources_are_list,
        f"count={len(raw_sources)}" if sources_are_list else "expected list",
    )
    sources = raw_sources if sources_are_list else []

    source_ids: List[str] = []
    malformed_entries: List[str] = []
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            malformed_entries.append(f"index={index}:{type(source).__name__}")
            continue
        source_id = source.get("id")
        if isinstance(source_id, str):
            source_ids.append(source_id)
        else:
            malformed_entries.append(f"index={index}:id={source_id!r}")

    invalid_source_ids = sorted(
        source_id
        for source_id in source_ids
        if re.fullmatch(r"S-\d{3,}", source_id) is None
    )
    duplicate_source_ids = sorted(
        source_id for source_id in set(source_ids) if source_ids.count(source_id) > 1
    )
    add_result(
        results,
        "source_register_source_ids",
        not malformed_entries
        and not invalid_source_ids
        and not duplicate_source_ids
        and len(source_ids) == len(sources),
        (
            f"ids={source_ids} invalid={invalid_source_ids} "
            f"duplicates={duplicate_source_ids} malformed={malformed_entries}"
        ),
    )
    registered_source_ids = {
        source_id
        for source_id in source_ids
        if re.fullmatch(r"S-\d{3,}", source_id) is not None
    }

    workspace_root = workspace.resolve()
    invalid_local_paths: List[str] = []
    invalid_urls: List[str] = []
    invalid_supports: List[str] = []
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            continue
        source_label = str(source.get("id") or f"index={index}")

        if "local_path" in source:
            local_path = source.get("local_path")
            if not isinstance(local_path, str) or not local_path.strip():
                invalid_local_paths.append(f"{source_label}:{local_path!r}")
            else:
                path_value = Path(local_path)
                windows_absolute = bool(
                    re.match(r"^(?:[A-Za-z]:[\\/]|\\\\)", local_path)
                )
                resolved_path = (workspace_root / path_value).resolve()
                try:
                    inside_workspace = resolved_path.is_relative_to(workspace_root)
                except ValueError:
                    inside_workspace = False
                if (
                    path_value.is_absolute()
                    or windows_absolute
                    or not inside_workspace
                    or not resolved_path.is_file()
                ):
                    invalid_local_paths.append(
                        f"{source_label}:{local_path} -> {resolved_path}"
                    )

        if "url" in source:
            url = source.get("url")
            parsed = urlparse(url) if isinstance(url, str) else None
            if (
                parsed is None
                or parsed.scheme.lower() != "https"
                or not parsed.netloc
            ):
                invalid_urls.append(f"{source_label}:{url!r}")

        supports = source.get("supports", [])
        if not isinstance(supports, list):
            invalid_supports.append(f"{source_label}:expected list")
            continue
        for evidence_id in supports:
            if (
                not isinstance(evidence_id, str)
                or re.fullmatch(r"E-\d{3,}", evidence_id) is None
                or evidence_id not in evidence_ids
            ):
                invalid_supports.append(f"{source_label}:{evidence_id!r}")

    add_result(
        results,
        "source_register_relative_paths",
        not invalid_local_paths,
        f"invalid={invalid_local_paths}",
    )
    add_result(
        results,
        "source_register_https_urls",
        not invalid_urls,
        f"invalid={invalid_urls}",
    )
    add_result(
        results,
        "source_register_supports_evidence",
        not invalid_supports,
        f"invalid={invalid_supports}",
    )

    proposal_source_ids: set[str] = set()
    proposal_read_error = ""
    if proposal_path.is_file():
        try:
            proposal_text = proposal_path.read_text(encoding="utf-8")
            proposal_source_ids = set(re.findall(r"\bS-\d{3,}\b", proposal_text))
        except (OSError, UnicodeError) as error:
            proposal_read_error = str(error)
    missing_source_ids = sorted(proposal_source_ids - registered_source_ids)
    add_result(
        results,
        "proposal_source_references",
        not proposal_read_error and not missing_source_ids,
        (
            f"referenced={sorted(proposal_source_ids)} "
            f"missing={missing_source_ids} read_error={proposal_read_error!r}"
        ),
    )


def validate_v2_workspace_metadata(
    workspace: Path,
    evidence_path: Path,
    proposal_path: Path,
    results: List[Dict[str, str]],
) -> None:
    manifest_path = workspace / "plan-manifest.yaml"
    source_register_path = workspace / "source-register.yaml"
    if not manifest_path.exists() and not source_register_path.exists():
        return

    manifest = read_yaml_mapping(manifest_path, "plan_manifest", results)
    source_register = read_yaml_mapping(
        source_register_path,
        "source_register",
        results,
    )
    validate_schema_version(manifest, "plan_manifest", results)
    validate_schema_version(source_register, "source_register", results)
    validate_source_register(
        workspace,
        source_register,
        read_evidence_ids(evidence_path),
        proposal_path,
        results,
    )


def validate_decision_log(path: Path, results: List[Dict[str, str]]) -> str:
    text = require_text_file(path, "decision_log", results)
    if not text:
        return text
    decision_ids = re.findall(r"(?m)^##\s+(D-\d+)\s*$", text)
    add_result(results, "decision_records", bool(decision_ids), f"ids={decision_ids}")
    has_status = bool(
        re.search(
            r"(?im)^\s*-\s+\*\*(?:Status|状态)\*\*:\s*(?:proposed|approved|superseded|已提议|已批准)",
            text,
        )
    )
    add_result(results, "decision_status", has_status, "proposed/approved/superseded")
    return text


def markdown_targets(text: str) -> Iterable[str]:
    for match in re.finditer(r"!?\[[^\]]*\]\(([^)]+)\)", text):
        target = match.group(1).strip()
        if target.startswith("<") and target.endswith(">"):
            target = target[1:-1].strip()
        if " \"" in target:
            target = target.split(" \"", 1)[0].strip()
        yield target


def validate_markdown_links(
    source: Path,
    text: str,
    results: List[Dict[str, str]],
) -> None:
    seen: set[str] = set()
    for raw_target in markdown_targets(text):
        if raw_target in seen:
            continue
        seen.add(raw_target)
        lower = raw_target.lower()
        if (
            lower.startswith(("http://", "https://", "mailto:", "tel:", "data:"))
            or raw_target.startswith("#")
        ):
            add_result(results, f"markdown_link:{raw_target}", True, "external-or-anchor")
            continue
        local_target = unquote(raw_target.split("#", 1)[0])
        resolved = (source.parent / local_target).resolve()
        add_result(
            results,
            f"markdown_link:{raw_target}",
            resolved.exists(),
            str(resolved),
        )


def validate_proposal(
    path: Path,
    required_groups: Sequence[str],
    evidence_ids: set[str],
    results: List[Dict[str, str]],
) -> str:
    text = require_text_file(path, "proposal", results)
    if not text:
        return text
    for group in required_groups:
        patterns = SECTION_GROUPS[group]
        found = any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)
        add_result(results, f"section:{group}", found, ", ".join(patterns))
    headings = re.findall(r"^##\s+(.+)$", text, flags=re.MULTILINE)
    minimum = 8 if len(required_groups) >= 8 else len(required_groups)
    add_result(results, "minimum_sections", len(headings) >= minimum, f"count={len(headings)}")
    validate_markdown_links(path, text, results)
    if evidence_ids:
        referenced = sorted(
            evidence_id for evidence_id in evidence_ids if evidence_id in text
        )
        add_result(
            results,
            "proposal_evidence_reference",
            bool(referenced),
            f"referenced={referenced}",
        )
    return text


def validate_diagram_artifact(path: Path, suffix: str) -> bool:
    if not path.is_file() or path.stat().st_size == 0:
        return False
    head = path.read_bytes()[:512]
    if suffix == ".png":
        return head.startswith(b"\x89PNG\r\n\x1a\n")
    if suffix == ".pdf":
        return head.startswith(b"%PDF")
    if suffix == ".svg":
        return b"<svg" in head.lower()
    return True


def validate_diagrams(directory: Path, results: List[Dict[str, str]]) -> None:
    if not directory.is_dir():
        add_result(results, "diagrams_dir", False, str(directory))
        return
    sources = sorted(directory.rglob("*.mmd"))
    add_result(results, "mermaid_sources", bool(sources), f"count={len(sources)}")
    for source in sources:
        candidates = [directory / "rendered", source.parent / "rendered", source.parent]
        for suffix in [".png", ".svg", ".pdf"]:
            matches = [
                candidate / f"{source.stem}{suffix}"
                for candidate in candidates
                if validate_diagram_artifact(candidate / f"{source.stem}{suffix}", suffix)
            ]
            add_result(
                results,
                f"diagram:{source.name}:{suffix}",
                bool(matches),
                str(matches[0]) if matches else "missing-or-invalid",
            )


def proposal_title(proposal_text: str) -> str:
    title_match = re.search(
        r"^title:\s*[\"']?(.+?)[\"']?\s*$",
        proposal_text,
        flags=re.MULTILINE,
    )
    return title_match.group(1).strip("\"'") if title_match else ""


def validate_pdf(
    path: Path,
    proposal_text: str,
    results: List[Dict[str, str]],
) -> int:
    if not path.is_file():
        add_result(results, "pdf_exists", False, str(path))
        return 0
    try:
        reader = PdfReader(str(path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except (OSError, ValueError) as error:
        add_result(results, "pdf_readable", False, str(error))
        return 0
    add_result(results, "pdf_exists", True, str(path))
    add_result(results, "pdf_page_count", len(reader.pages) >= 3, f"pages={len(reader.pages)}")
    add_result(results, "pdf_text", len(text.strip()) >= 300, f"characters={len(text)}")
    title = proposal_title(proposal_text)
    if title:
        add_result(results, "pdf_title", title in text, title)
    duplicate = bool(re.search(r"\b(\d+)\.\s+\1\.", text))
    add_result(results, "toc_duplicate_numbering", not duplicate, f"duplicate={duplicate}")
    add_result(results, "pdf_sha256", True, sha256(path))
    return len(reader.pages)


def validate_rendered_pages(
    directory: Path,
    expected_pages: int,
    results: List[Dict[str, str]],
) -> None:
    if not directory.is_dir():
        add_result(results, "rendered_pages_dir", False, str(directory))
        return
    images = sorted(directory.glob("page-*.png"))
    add_result(
        results,
        "rendered_page_count",
        expected_pages > 0 and len(images) == expected_pages,
        f"images={len(images)} expected={expected_pages}",
    )


def validate_delivered_copy(
    source: Path,
    delivered: Path,
    results: List[Dict[str, str]],
) -> None:
    if not delivered.is_file():
        add_result(results, "delivered_pdf_exists", False, str(delivered))
        return
    source_hash = sha256(source) if source.is_file() else ""
    delivered_hash = sha256(delivered)
    add_result(
        results,
        "delivered_pdf_sha256",
        bool(source_hash) and source_hash == delivered_hash,
        f"source={source_hash} delivered={delivered_hash}",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a create-plan-skill workspace by operating mode."
    )
    parser.add_argument("--mode", choices=MODES, default="full-proposal")
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--brief", type=Path)
    parser.add_argument("--evidence-register", type=Path)
    parser.add_argument("--decision-log", type=Path)
    parser.add_argument("--proposal", type=Path)
    parser.add_argument("--pdf", type=Path)
    parser.add_argument("--diagrams-dir", type=Path)
    parser.add_argument("--rendered-pages-dir", type=Path)
    parser.add_argument("--delivered-pdf", type=Path)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def resolved(path: Path | None) -> Path | None:
    return path.expanduser().resolve() if path else None


def main() -> int:
    args = parse_args()
    workspace = resolved(args.workspace)
    if workspace is None:
        explicit_proposal = resolved(args.proposal)
        workspace = explicit_proposal.parent if explicit_proposal else Path.cwd().resolve()

    artifacts = {
        "brief": resolved(args.brief) or workspace / "brief.md",
        "evidence": resolved(args.evidence_register) or workspace / "evidence-register.md",
        "decision": resolved(args.decision_log) or workspace / "decision-log.md",
        "proposal": resolved(args.proposal) or workspace / "proposal.md",
        "pdf": resolved(args.pdf) or workspace / "output" / "pdf" / "formal-plan.pdf",
        "diagrams": resolved(args.diagrams_dir) or workspace / "diagrams",
    }
    results: List[Dict[str, str]] = []
    proposal_text = ""
    evidence_ids: set[str] = set()
    page_count = 0

    validate_v2_workspace_metadata(
        workspace,
        artifacts["evidence"],
        artifacts["proposal"],
        results,
    )

    if args.mode == "discovery-only":
        validate_brief(artifacts["brief"], results)
    elif args.mode == "research-and-options":
        validate_brief(artifacts["brief"], results)
        evidence_ids = validate_evidence_register(artifacts["evidence"], results)
        validate_decision_log(artifacts["decision"], results)
        validate_proposal(
            artifacts["proposal"],
            RESEARCH_SECTIONS,
            evidence_ids,
            results,
        )
    elif args.mode == "full-proposal":
        validate_brief(artifacts["brief"], results)
        evidence_ids = validate_evidence_register(artifacts["evidence"], results)
        validate_decision_log(artifacts["decision"], results)
        proposal_text = validate_proposal(
            artifacts["proposal"],
            FULL_SECTIONS,
            evidence_ids,
            results,
        )
        validate_diagrams(artifacts["diagrams"], results)
        page_count = validate_pdf(artifacts["pdf"], proposal_text, results)
    else:
        validated_any = False
        if artifacts["brief"].is_file():
            validate_brief(artifacts["brief"], results)
            validated_any = True
        if artifacts["evidence"].is_file():
            evidence_ids = validate_evidence_register(artifacts["evidence"], results)
            validated_any = True
        if artifacts["decision"].is_file():
            validate_decision_log(artifacts["decision"], results)
            validated_any = True
        if artifacts["proposal"].is_file():
            proposal_text = validate_proposal(
                artifacts["proposal"],
                (),
                evidence_ids,
                results,
            )
            validated_any = True
        if artifacts["diagrams"].is_dir():
            validate_diagrams(artifacts["diagrams"], results)
            validated_any = True
        if artifacts["pdf"].is_file():
            page_count = validate_pdf(artifacts["pdf"], proposal_text, results)
            validated_any = True
        add_result(results, "validation_target", validated_any, str(workspace))

    rendered_pages = resolved(args.rendered_pages_dir)
    if rendered_pages:
        validate_rendered_pages(rendered_pages, page_count, results)

    delivered_pdf = resolved(args.delivered_pdf)
    if delivered_pdf:
        validate_delivered_copy(artifacts["pdf"], delivered_pdf, results)

    failures = [result for result in results if result["status"] == "FAIL"]
    if args.json:
        print(
            json.dumps(
                {
                    "mode": args.mode,
                    "workspace": str(workspace),
                    "results": results,
                    "failures": len(failures),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        for result in results:
            print(f"{result['status']} {result['check']}: {result['details']}")
        print(f"mode={args.mode}")
        print(f"failures={len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
