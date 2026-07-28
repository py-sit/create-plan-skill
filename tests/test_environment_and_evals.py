from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


class EnvironmentAndEvalTests(unittest.TestCase):
    def test_environment_check_returns_machine_readable_capabilities(self) -> None:
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
        self.assertIn("python", payload)
        self.assertIn("python_packages", payload)
        self.assertIn("mermaid", payload)
        self.assertIn("pdf_pages", payload)
        self.assertIn("font", payload)
        self.assertEqual(
            payload["python_packages"]["Pillow"]["expected"],
            "11.3.0",
        )
        self.assertTrue(payload["python_packages"]["Pillow"]["matches_pin"])

    def test_eval_schema_validator_passes_repository_cases(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "validate_evals.py"),
                str(ROOT / "evals" / "cases.jsonl"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("cases=", result.stdout)
        self.assertIn("failures=0", result.stdout)


if __name__ == "__main__":
    unittest.main()
