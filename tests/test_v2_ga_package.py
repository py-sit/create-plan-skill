from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]


class V2GAPackageTests(unittest.TestCase):
    def test_release_package_is_deterministic_installable_and_private_path_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary)
            command = [
                sys.executable,
                str(ROOT / "scripts" / "package_plugin.py"),
                "--output-dir",
                str(output_dir),
            ]
            first = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            archive = output_dir / "create-plan-skill-2.0.0.zip"
            checksum = output_dir / "create-plan-skill-2.0.0.zip.sha256"
            self.assertTrue(archive.is_file())
            self.assertTrue(checksum.is_file())
            first_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
            self.assertEqual(checksum.read_text(encoding="utf-8").split()[0], first_hash)

            second = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), first_hash)

            with zipfile.ZipFile(archive) as package:
                names = set(package.namelist())
            required = {
                ".codex-plugin/plugin.json",
                "skills/create-plan-skill/SKILL.md",
                "skills/clarify-plan-requirements/SKILL.md",
                "skills/research-plan-options/SKILL.md",
                "skills/author-formal-plan/SKILL.md",
                "skills/validate-plan-package/SKILL.md",
                "scripts/install_skills.py",
                "README.md",
                "license.txt",
            }
            self.assertTrue(required.issubset(names), required - names)
            self.assertFalse(any(name.startswith("/") or ".." in Path(name).parts for name in names))

            validation = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "validate_release_package.py"),
                    str(archive),
                    "--json",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(
                validation.returncode,
                0,
                validation.stdout + validation.stderr,
            )
            payload = json.loads(validation.stdout)
            self.assertEqual(payload["version"], "2.0.0")
            self.assertEqual(payload["failures"], [])

    def test_release_installer_upgrades_v11_with_backup(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            codex_root = root / "codex-skills"
            agents_root = root / "agents-skills"
            legacy = codex_root / "create-plan-skill"
            legacy.mkdir(parents=True)
            (legacy / "SKILL.md").write_text(
                "---\nname: create-plan-skill\n"
                "description: Use when legacy plans are requested.\n"
                "---\n# Legacy\n",
                encoding="utf-8",
            )
            dry_run = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "install_skills.py"),
                    "--codex-root",
                    str(codex_root),
                    "--agents-root",
                    str(agents_root),
                    "--json",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(dry_run.returncode, 0, dry_run.stdout + dry_run.stderr)
            self.assertTrue(json.loads(dry_run.stdout)["dry_run"])
            self.assertIn("Legacy", (legacy / "SKILL.md").read_text(encoding="utf-8"))

            applied = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "install_skills.py"),
                    "--codex-root",
                    str(codex_root),
                    "--agents-root",
                    str(agents_root),
                    "--apply",
                    "--upgrade",
                    "--json",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
            payload = json.loads(applied.stdout)
            self.assertEqual(len(payload["installed"]), 10)
            for destination in (codex_root, agents_root):
                for name in (
                    "create-plan-skill",
                    "clarify-plan-requirements",
                    "research-plan-options",
                    "author-formal-plan",
                    "validate-plan-package",
                ):
                    self.assertTrue((destination / name / "SKILL.md").is_file())
            backups = list((codex_root / ".create-plan-backups").rglob("SKILL.md"))
            self.assertEqual(len(backups), 1)
            self.assertIn("Legacy", backups[0].read_text(encoding="utf-8"))

    def test_public_documentation_matches_ga_version(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        release_notes = (
            ROOT / "docs" / "release-v2.0.0.md"
        ).read_text(encoding="utf-8")
        self.assertIn("2.0.0", readme)
        self.assertIn("Alpha", release_notes)
        self.assertIn("Beta", release_notes)
        self.assertIn("RC", release_notes)
        self.assertIn("GA", release_notes)
        self.assertIn("install_skills.py", readme)
        self.assertNotIn("/Users/yrpy", readme + release_notes)


if __name__ == "__main__":
    unittest.main()
