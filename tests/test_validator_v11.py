from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_plan_package.py"


def write_pdf(path: Path, title: str, marker: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = canvas.Canvas(str(path))
    document.setTitle(title)
    for page in range(3):
        document.drawString(72, 760, title)
        document.drawString(72, 730, f"{marker} page {page + 1}")
        document.drawString(
            72,
            700,
            (
                "This page contains substantive validation text for the formal "
                "proposal package. "
            )
            * 3,
        )
        document.showPage()
    document.save()


def write_full_workspace(root: Path) -> None:
    (root / "references").mkdir(parents=True)
    (root / "diagrams" / "rendered").mkdir(parents=True)
    (root / "output" / "pdf").mkdir(parents=True)

    (root / "brief.md").write_text(
        """# Confirmed Brief

## Outcome
Approved decision.

## Audience
Review board.

## Current problem
Current process is manual.

## Acceptance criteria
The report is reviewable.
""",
        encoding="utf-8",
    )
    (root / "evidence-register.md").write_text(
        """# Evidence Register

| ID | Claim | Label | Source | Freshness | Impact |
| --- | --- | --- | --- | --- | --- |
| E-001 | Current process is manual | Confirmed requirement | User confirmation | 2026-07-28 | Workflow |
""",
        encoding="utf-8",
    )
    (root / "decision-log.md").write_text(
        """# Decision Log

## D-001

- **Decision**: Use option B.
- **Status**: approved
- **Context**: Review workflow.
- **Options considered**: A and B.
- **Selected option**: B.
- **Why**: Better auditability.
- **Trade-offs**: More review time.
- **Failure boundary**: Stop when evidence is insufficient.
- **Rollback or exit strategy**: Return to manual review.
- **Validation needed**: Pilot review.
""",
        encoding="utf-8",
    )
    (root / "references" / "source.md").write_text(
        "# Source\n\nPrimary evidence.\n",
        encoding="utf-8",
    )
    (root / "proposal.md").write_text(
        """---
title: "Validation Plan"
language: "en-US"
---

# Validation Plan

## 1. Executive Summary
Summary with evidence E-001 and [source](references/source.md).

## 2. Requirements
Requirements.

## 3. Alternatives
Options.

## 4. Architecture
Architecture.

## 5. Security
Security.

## 6. Acceptance
Acceptance.

## 7. Risks
Risks.

## 8. Final Recommendation
Recommendation.
""",
        encoding="utf-8",
    )
    (root / "diagrams" / "architecture.mmd").write_text(
        'flowchart LR\n  A["Input"] --> B["Output"]\n',
        encoding="utf-8",
    )
    Image.new("RGB", (800, 500), "white").save(
        root / "diagrams" / "rendered" / "architecture.png"
    )
    write_pdf(
        root / "diagrams" / "rendered" / "architecture.pdf",
        "Architecture",
        "diagram",
    )
    write_pdf(
        root / "output" / "pdf" / "formal-plan.pdf",
        "Validation Plan",
        "proposal",
    )


class ValidatorV11Tests(unittest.TestCase):
    def run_validator(self, workspace: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(VALIDATOR),
                "--mode",
                "full-proposal",
                "--workspace",
                str(workspace),
                *extra,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_full_proposal_requires_svg_and_accepts_complete_package(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            write_full_workspace(workspace)

            missing_svg = self.run_validator(workspace)
            self.assertEqual(missing_svg.returncode, 1)
            self.assertIn("diagram:architecture.mmd:.svg", missing_svg.stdout)

            (workspace / "diagrams" / "rendered" / "architecture.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"></svg>',
                encoding="utf-8",
            )
            complete = self.run_validator(workspace)
            self.assertEqual(complete.returncode, 0, complete.stdout + complete.stderr)

    def test_missing_local_markdown_link_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            write_full_workspace(workspace)
            (workspace / "diagrams" / "rendered" / "architecture.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"></svg>',
                encoding="utf-8",
            )
            proposal = workspace / "proposal.md"
            proposal.write_text(
                proposal.read_text(encoding="utf-8")
                + "\n[missing evidence](references/missing.md)\n",
                encoding="utf-8",
            )

            result = self.run_validator(workspace)
            self.assertEqual(result.returncode, 1)
            self.assertIn("markdown_link:references/missing.md", result.stdout)

    def test_delivered_pdf_hash_mismatch_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            write_full_workspace(workspace)
            (workspace / "diagrams" / "rendered" / "architecture.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"></svg>',
                encoding="utf-8",
            )
            delivered = workspace / "delivered.pdf"
            write_pdf(delivered, "Different", "different")

            result = self.run_validator(
                workspace,
                "--delivered-pdf",
                str(delivered),
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("delivered_pdf_sha256", result.stdout)

    def test_discovery_mode_does_not_require_pdf_or_diagrams(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            (workspace / "brief.md").write_text(
                """# Confirmed Brief

## Outcome
Decision.

## Audience
Sponsor.

## Current problem
Manual process.

## Acceptance criteria
Approved brief.
""",
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATOR),
                    "--mode",
                    "discovery-only",
                    "--workspace",
                    str(workspace),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn("pdf_exists", result.stdout)
            self.assertNotIn("mermaid_sources", result.stdout)


if __name__ == "__main__":
    unittest.main()
