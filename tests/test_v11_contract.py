from __future__ import annotations

import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


def frontmatter_value(text: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}:\s*(.+?)\s*$", text, flags=re.MULTILINE)
    if not match:
        return ""
    return match.group(1).strip().strip("\"'")


class V11ContractTests(unittest.TestCase):
    def test_skill_metadata_is_trigger_focused_and_versioned(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        description = frontmatter_value(text, "description")

        self.assertTrue(description.startswith("Use when"))
        self.assertLessEqual(len(description), 400)
        self.assertNotIn("option-research", description)
        self.assertEqual(frontmatter_value(text, "license"), "MIT")
        self.assertRegex(text, r'(?m)^\s+compatibility:\s*["\']Python 3\.9\+;')
        self.assertRegex(text, r'(?m)^\s+version:\s*["\']1\.1\.0["\']\s*$')
        self.assertIn("generic GitHub repository search", text)

    def test_implicit_invocation_is_disabled_until_router_split(self) -> None:
        metadata = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn("allow_implicit_invocation: false", metadata)

    def test_bilingual_templates_and_v11_tools_exist(self) -> None:
        expected = [
            ROOT / "assets" / "formal-plan-template.zh-CN.md",
            ROOT / "assets" / "formal-plan-template.en-US.md",
            ROOT / "scripts" / "check_environment.py",
            ROOT / "scripts" / "render_pdf_pages.py",
            ROOT / "scripts" / "create_pdf_contact_sheet.py",
            ROOT / "scripts" / "validate_evals.py",
        ]
        for path in expected:
            with self.subTest(path=path):
                self.assertTrue(path.is_file(), str(path))

    def test_python_dependencies_are_exactly_pinned(self) -> None:
        requirements = [
            line.strip()
            for line in (ROOT / "scripts" / "requirements.txt")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        self.assertGreaterEqual(len(requirements), 3)
        for requirement in requirements:
            with self.subTest(requirement=requirement):
                self.assertRegex(requirement, r"^[A-Za-z0-9_.-]+==[A-Za-z0-9_.+-]+$")

    def test_eval_suite_has_balanced_trigger_and_mode_coverage(self) -> None:
        cases_path = ROOT / "evals" / "cases.jsonl"
        self.assertTrue(cases_path.is_file())
        cases = [
            json.loads(line)
            for line in cases_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertGreaterEqual(len(cases), 12)
        self.assertLessEqual(len(cases), 20)
        self.assertEqual(len({case["id"] for case in cases}), len(cases))
        self.assertEqual({case["should_trigger"] for case in cases}, {True, False})
        triggered_modes = {
            case["expected_mode"] for case in cases if case["should_trigger"]
        }
        self.assertTrue(
            {
                "discovery-only",
                "research-and-options",
                "full-proposal",
                "validation-only",
            }.issubset(triggered_modes)
        )


if __name__ == "__main__":
    unittest.main()
