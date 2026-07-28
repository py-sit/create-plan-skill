#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Dict, Iterable, List, Sequence
from urllib.parse import unquote

try:
    from pypdf import PdfReader
except ImportError as error:
    print("ERROR: Missing pypdf. Install scripts/requirements.txt.", file=sys.stderr)
    raise SystemExit(2) from error


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
