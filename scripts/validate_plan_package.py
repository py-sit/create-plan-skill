#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Dict, List

try:
    from pypdf import PdfReader
except ImportError as error:
    print("ERROR: Missing pypdf. Install it before validation.", file=sys.stderr)
    raise SystemExit(2) from error


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
    "alternatives": [r"方案选型", r"方案对比", r"Alternatives", r"Options"],
    "architecture": [r"架构", r"Architecture"],
    "security": [r"安全", r"隐私", r"Security", r"Privacy"],
    "acceptance": [r"验收", r"Acceptance"],
    "risks": [r"风险", r"Risks?"],
    "recommendation": [r"最终建议", r"Final Recommendation", r"Recommendation"],
}


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


def validate_proposal(path: Path, results: List[Dict[str, str]]) -> str:
    text = path.read_text(encoding="utf-8")
    add_result(results, "proposal_exists", True, str(path))
    for pattern in PLACEHOLDER_PATTERNS:
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        add_result(
            results,
            f"placeholder:{pattern}",
            not matches,
            f"matches={matches[:5]}",
        )
    for group, patterns in SECTION_GROUPS.items():
        found = any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)
        add_result(results, f"section:{group}", found, ", ".join(patterns))
    headings = re.findall(r"^##\s+(.+)$", text, flags=re.MULTILINE)
    add_result(results, "minimum_sections", len(headings) >= 8, f"count={len(headings)}")
    return text


def validate_diagrams(directory: Path, results: List[Dict[str, str]]) -> None:
    sources = sorted(directory.rglob("*.mmd"))
    add_result(results, "mermaid_sources", bool(sources), f"count={len(sources)}")
    for source in sources:
        candidates = [directory / "rendered", source.parent / "rendered", source.parent]
        for suffix in [".png", ".pdf"]:
            matches = [
                candidate / f"{source.stem}{suffix}"
                for candidate in candidates
                if (candidate / f"{source.stem}{suffix}").is_file()
            ]
            add_result(
                results,
                f"diagram:{source.name}:{suffix}",
                bool(matches),
                str(matches[0]) if matches else "missing",
            )


def validate_pdf(
    path: Path,
    proposal_text: str,
    results: List[Dict[str, str]],
) -> None:
    reader = PdfReader(str(path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    title_match = re.search(r"^title:\s*[\"']?(.+?)[\"']?\s*$", proposal_text, re.MULTILINE)
    title = title_match.group(1).strip("\"'") if title_match else ""
    add_result(results, "pdf_exists", True, str(path))
    add_result(results, "pdf_page_count", len(reader.pages) >= 3, f"pages={len(reader.pages)}")
    add_result(results, "pdf_text", len(text.strip()) >= 300, f"characters={len(text)}")
    if title:
        add_result(results, "pdf_title", title in text, title)
    duplicate = bool(re.search(r"\b(\d+)\.\s+\1\.", text))
    add_result(results, "toc_duplicate_numbering", not duplicate, f"duplicate={duplicate}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    add_result(results, "pdf_sha256", True, digest)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a formal proposal source, diagrams, and PDF."
    )
    parser.add_argument("--proposal", required=True, type=Path)
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--diagrams-dir", type=Path)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    proposal = args.proposal.expanduser().resolve()
    pdf = args.pdf.expanduser().resolve()
    results: List[Dict[str, str]] = []

    if not proposal.is_file():
        add_result(results, "proposal_exists", False, str(proposal))
        proposal_text = ""
    else:
        proposal_text = validate_proposal(proposal, results)

    if args.diagrams_dir:
        diagrams_dir = args.diagrams_dir.expanduser().resolve()
        if diagrams_dir.is_dir():
            validate_diagrams(diagrams_dir, results)
        else:
            add_result(results, "diagrams_dir", False, str(diagrams_dir))

    if not pdf.is_file():
        add_result(results, "pdf_exists", False, str(pdf))
    else:
        validate_pdf(pdf, proposal_text, results)

    failures = [result for result in results if result["status"] == "FAIL"]
    if args.json:
        print(json.dumps({"results": results, "failures": len(failures)}, ensure_ascii=False, indent=2))
    else:
        for result in results:
            print(f"{result['status']} {result['check']}: {result['details']}")
        print(f"failures={len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
