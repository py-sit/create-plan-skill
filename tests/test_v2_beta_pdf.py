from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

from pypdf import PdfReader
import yaml


ROOT = Path(__file__).resolve().parents[1]


def pdf_uris(path: Path) -> list[str]:
    uris: list[str] = []
    reader = PdfReader(str(path))
    for page in reader.pages:
        for annotation_reference in page.get("/Annots", []):
            annotation = annotation_reference.get_object()
            action = annotation.get("/A")
            if action and action.get("/URI"):
                uris.append(str(action.get("/URI")))
    return uris


class V2BetaPdfTests(unittest.TestCase):
    def create_workspace(self, root: Path, language: str = "en-US") -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "init_plan_workspace.py"),
                "--output-dir",
                str(root),
                "--title",
                "Evidence Rendering Plan",
                "--language",
                language,
                "--theme",
                "corporate-blue",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        references = root / "references"
        (references / "local-source.md").write_text(
            "# Local source\n\nA workspace-local source.",
            encoding="utf-8",
        )
        (root / "source-register.yaml").write_text(
            yaml.safe_dump(
                {
                    "schema_version": "2.0",
                    "sources": [
                        {
                            "id": "S-001",
                            "title": "Playwright PDF documentation",
                            "kind": "official-doc",
                            "url": "https://playwright.dev/python/docs/api/class-page",
                            "publisher": "Microsoft",
                            "accessed": "2026-07-28",
                            "version": "1.60",
                            "license": "Apache-2.0",
                            "supports": ["E-001"],
                            "notes": "Primary renderer API.",
                        },
                        {
                            "id": "S-002",
                            "title": "Local evidence",
                            "kind": "project-file",
                            "local_path": "references/local-source.md",
                            "publisher": "Project",
                            "accessed": "2026-07-28",
                            "version": "current",
                            "license": "internal",
                            "supports": ["E-001"],
                            "notes": "Workspace-relative evidence.",
                        },
                    ],
                },
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        (root / "brief.md").write_text(
            """# Confirmed Brief

## Outcome
Approve a renderer.

## Audience
Review board.

## Current problem
The document needs stable visual output.

## Acceptance criteria
The package is traceable and readable.
""",
            encoding="utf-8",
        )
        (root / "evidence-register.md").write_text(
            """# Evidence Register

| ID | Claim | Label | Source | Freshness | Impact |
| --- | --- | --- | --- | --- | --- |
| E-001 | Playwright supports PDF output | verified | S-001, S-002 | 2026-07-28 | Rendering |
""",
            encoding="utf-8",
        )
        (root / "decision-log.md").write_text(
            """# Decision Log

## D-001

- **Decision**: Use Playwright.
- **Status**: approved
- **Context**: PDF rendering.
- **Options considered**: Playwright and ReportLab.
- **Selected option**: Playwright.
- **Why**: Better HTML/CSS fidelity.
- **Trade-offs**: Requires Chromium.
- **Failure boundary**: Stop if the browser is unavailable.
- **Rollback or exit strategy**: Explicit ReportLab fallback.
- **Validation needed**: Visual review.
""",
            encoding="utf-8",
        )
        local_link = "references/local-source.md"
        proposal = root / "proposal.md"
        proposal.write_text(
            f"""---
title: "Evidence Rendering Plan"
subtitle: "V2 Beta"
language: "{language}"
version: "V2.0"
status: "Draft for Review"
---

# Evidence Rendering Plan

## 1. Executive Summary
Use Playwright based on E-001 and S-001.

## 2. Requirements
Keep [local evidence]({local_link}) relative and preserve the
[official link](https://playwright.dev/python/docs/api/class-page).

## 3. Alternatives
Playwright is primary. ReportLab is fallback.

## 4. Architecture
Markdown becomes safe HTML and then PDF.

## 5. Security
Rendering blocks outbound network requests.

## 6. Acceptance
The PDF is readable and traceable.

## 7. Risks
Chromium may be unavailable.

## 8. Final Recommendation
Adopt the primary renderer with explicit fallback.
""",
            encoding="utf-8",
        )

    def test_theme_files_exist_and_define_print_contract(self) -> None:
        expected = {
            "corporate-blue.css",
            "executive-slate.css",
            "minimal-mono.css",
        }
        actual = {path.name for path in (ROOT / "shared" / "themes").glob("*.css")}
        self.assertEqual(actual, expected)
        for name in sorted(expected):
            text = (ROOT / "shared" / "themes" / name).read_text(encoding="utf-8")
            self.assertIn("@page", text)
            self.assertIn("--brand-color", text)
            self.assertIn("print-color-adjust", text)

    def test_v2_dependencies_and_environment_are_reported_separately(self) -> None:
        requirements = [
            line.strip()
            for line in (ROOT / "scripts" / "requirements-v2.txt")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip() and not line.startswith("#")
        ]
        self.assertIn("playwright==1.60.0", requirements)
        self.assertIn("Markdown==3.9", requirements)
        self.assertIn("PyYAML==6.0.3", requirements)
        legacy = (ROOT / "scripts" / "requirements.txt").read_text(encoding="utf-8")
        self.assertNotIn("playwright", legacy.lower())
        self.assertNotIn("pyyaml", legacy.lower())

        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "check_environment.py"),
                "--json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["v2_pdf"]["playwright"]["expected"], "1.60.0")
        self.assertEqual(payload["v2_pdf"]["markdown"]["expected"], "3.9")
        self.assertTrue(payload["v2_pdf"]["browser"]["path"])

    def test_playwright_renderer_creates_traceable_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            self.create_workspace(workspace)
            output = workspace / "output" / "pdf" / "formal-plan.pdf"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "render_plan_pdf.py"),
                    str(workspace / "proposal.md"),
                    "--output",
                    str(output),
                    "--engine",
                    "playwright",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("engine=playwright", result.stdout)
            self.assertTrue(output.is_file())
            reader = PdfReader(str(output))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            self.assertIn("Evidence Rendering Plan", text)
            self.assertIn("References", text)
            self.assertIn("S-001", text)
            uris = pdf_uris(output)
            self.assertIn(
                "https://playwright.dev/python/docs/api/class-page",
                uris,
            )
            self.assertFalse(any(uri.startswith("file://") for uri in uris))

            manifest = yaml.safe_load(
                (workspace / "plan-manifest.yaml").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["render"]["engine"], "playwright")
            self.assertEqual(manifest["theme"], "corporate-blue")
            self.assertRegex(manifest["artifacts"]["pdf_sha256"], r"^[0-9a-f]{64}$")

    def test_v2_validator_checks_source_references_and_relative_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            self.create_workspace(workspace)
            register = yaml.safe_load(
                (workspace / "source-register.yaml").read_text(encoding="utf-8")
            )
            register["sources"][1]["local_path"] = "/Users/example/private/source.md"
            (workspace / "source-register.yaml").write_text(
                yaml.safe_dump(register, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "validate_plan_package.py"),
                    "--mode",
                    "research-and-options",
                    "--workspace",
                    str(workspace),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("source_register_relative_paths", result.stdout)


if __name__ == "__main__":
    unittest.main()
