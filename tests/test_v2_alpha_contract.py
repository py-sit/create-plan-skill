from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILL_VALIDATOR = (
    Path.home()
    / ".codex"
    / "skills"
    / ".system"
    / "skill-creator"
    / "scripts"
    / "quick_validate.py"
)
PLUGIN_VALIDATOR = (
    Path.home()
    / ".codex"
    / "skills"
    / ".system"
    / "plugin-creator"
    / "scripts"
    / "validate_plugin.py"
)

PLUGIN_SKILLS = {
    "create-plan-skill",
    "clarify-plan-requirements",
    "research-plan-options",
    "author-formal-plan",
    "validate-plan-package",
}
SPECIALIST_SKILLS = PLUGIN_SKILLS - {"create-plan-skill"}


class V2AlphaContractTests(unittest.TestCase):
    def test_plugin_manifest_is_valid_v2(self) -> None:
        manifest_path = ROOT / ".codex-plugin" / "plugin.json"
        self.assertTrue(manifest_path.is_file())
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "create-plan-skill")
        self.assertEqual(manifest["version"], "2.0.0")
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertNotIn("hooks", manifest)

        result = subprocess.run(
            [sys.executable, str(PLUGIN_VALIDATOR), str(ROOT)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_router_and_specialist_skills_are_valid(self) -> None:
        actual = {
            path.parent.name
            for path in (ROOT / "skills").glob("*/SKILL.md")
        }
        self.assertEqual(actual, PLUGIN_SKILLS)
        for skill_name in sorted(actual):
            with self.subTest(skill=skill_name):
                result = subprocess.run(
                    [
                        sys.executable,
                        str(SKILL_VALIDATOR),
                        str(ROOT / "skills" / skill_name),
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_router_is_thin_and_names_every_specialist(self) -> None:
        router = (
            ROOT / "skills" / "create-plan-skill" / "SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertLessEqual(len(router.splitlines()), 180)
        for skill_name in sorted(SPECIALIST_SKILLS):
            self.assertIn(f"${skill_name}", router)
        self.assertIn("Do not expose private chain-of-thought", router)

    def test_specialists_are_explicit_only(self) -> None:
        for skill_name in sorted(SPECIALIST_SKILLS):
            with self.subTest(skill=skill_name):
                metadata = (
                    ROOT / "skills" / skill_name / "agents" / "openai.yaml"
                ).read_text(encoding="utf-8")
                self.assertIn("allow_implicit_invocation: false", metadata)

    def test_v11_root_contract_remains_available(self) -> None:
        legacy = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn('version: "1.1.0"', legacy)
        self.assertTrue((ROOT / "scripts" / "render_plan_pdf.py").is_file())
        self.assertTrue((ROOT / "assets" / "formal-plan-template.zh-CN.md").is_file())

    def test_workspace_contains_v2_manifest_and_source_register(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "init_plan_workspace.py"),
                    "--output-dir",
                    str(workspace),
                    "--title",
                    "Alpha Contract",
                    "--language",
                    "en-US",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            manifest = yaml.safe_load(
                (workspace / "plan-manifest.yaml").read_text(encoding="utf-8")
            )
            sources = yaml.safe_load(
                (workspace / "source-register.yaml").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["schema_version"], "2.0")
            self.assertEqual(manifest["mode"], "full-proposal")
            self.assertEqual(manifest["language"], "en-US")
            self.assertEqual(manifest["render"]["engine"], "playwright")
            self.assertEqual(sources["schema_version"], "2.0")
            self.assertEqual(sources["sources"], [])

    def test_workspace_schemas_are_valid_json_schema_documents(self) -> None:
        for name in ("plan-manifest.schema.json", "source-register.schema.json"):
            with self.subTest(schema=name):
                schema = json.loads(
                    (ROOT / "shared" / "schemas" / name).read_text(encoding="utf-8")
                )
                self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
                self.assertEqual(schema["type"], "object")
                self.assertIn("required", schema)


if __name__ == "__main__":
    unittest.main()
