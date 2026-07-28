from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class V2ReleaseCandidateTests(unittest.TestCase):
    def test_v2_eval_suite_and_router_metrics_meet_gate(self) -> None:
        cases = ROOT / "evals" / "v2" / "cases.jsonl"
        validation = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "validate_evals.py"),
                str(cases),
                "--profile",
                "v2",
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
        self.assertIn("cases=", validation.stdout)
        count = int(
            next(
                line.split("=", 1)[1]
                for line in validation.stdout.splitlines()
                if line.startswith("cases=")
            )
        )
        self.assertGreaterEqual(count, 30)

        evaluation = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "evaluate_router.py"),
                str(cases),
                "--json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            evaluation.returncode,
            0,
            evaluation.stdout + evaluation.stderr,
        )
        metrics = json.loads(evaluation.stdout)
        self.assertGreaterEqual(metrics["trigger_precision"], 0.95)
        self.assertGreaterEqual(metrics["trigger_recall"], 0.95)
        self.assertGreaterEqual(metrics["mode_accuracy"], 0.95)

    def test_v11_workspace_migration_is_dry_run_idempotent_and_lossless(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            initialized = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "init_plan_workspace.py"),
                    "--output-dir",
                    str(workspace),
                    "--title",
                    "Legacy Workspace",
                    "--language",
                    "zh-CN",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(
                initialized.returncode,
                0,
                initialized.stdout + initialized.stderr,
            )
            (workspace / "plan-manifest.yaml").unlink()
            (workspace / "source-register.yaml").unlink()
            original_files = {
                path.relative_to(workspace): file_hash(path)
                for path in workspace.rglob("*")
                if path.is_file()
            }

            dry_run = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "migrate_v11_workspace.py"),
                    str(workspace),
                    "--json",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(dry_run.returncode, 0, dry_run.stdout + dry_run.stderr)
            self.assertFalse((workspace / "plan-manifest.yaml").exists())
            self.assertTrue(json.loads(dry_run.stdout)["dry_run"])

            applied = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "migrate_v11_workspace.py"),
                    str(workspace),
                    "--apply",
                    "--json",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
            self.assertTrue((workspace / "plan-manifest.yaml").is_file())
            self.assertTrue((workspace / "source-register.yaml").is_file())
            for relative, digest in original_files.items():
                with self.subTest(file=relative):
                    self.assertEqual(file_hash(workspace / relative), digest)

            second = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "migrate_v11_workspace.py"),
                    str(workspace),
                    "--apply",
                    "--json",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertEqual(json.loads(second.stdout)["created"], [])

    def test_sensitive_scanner_redacts_values(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            secret = "ghp_" + "A" * 36
            (root / "unsafe.txt").write_text(
                f"token={secret}\npath=/Users/private-user/confidential.txt\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "scan_sensitive_content.py"),
                    str(root),
                    "--json",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 1)
            self.assertNotIn(secret, result.stdout)
            payload = json.loads(result.stdout)
            rules = {finding["rule"] for finding in payload["findings"]}
            self.assertIn("github-token", rules)
            self.assertIn("local-absolute-path", rules)
            self.assertTrue(
                all("match_sha256" in finding for finding in payload["findings"])
            )

    def test_bilingual_playwright_visual_baselines(self) -> None:
        baselines = yaml.safe_load(
            (ROOT / "evals" / "visual-baselines.yaml").read_text(encoding="utf-8")
        )
        for language in ("zh-CN", "en-US"):
            with self.subTest(language=language), tempfile.TemporaryDirectory() as temporary:
                workspace = Path(temporary)
                init = subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "scripts" / "init_plan_workspace.py"),
                        "--output-dir",
                        str(workspace),
                        "--title",
                        "视觉基线方案" if language == "zh-CN" else "Visual Baseline Plan",
                        "--language",
                        language,
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
                proposal = workspace / "proposal.md"
                if language == "zh-CN":
                    body = """---
title: "视觉基线方案"
subtitle: "正式评审稿"
language: "zh-CN"
version: "V2.0"
recommendation: "采用分阶段交付并保留人工确认"
---

# 视觉基线方案

## 1. 执行摘要
本方案用于验证正式报告的版式、颜色、分页和中文字体。

## 2. 需求
报告必须清晰、可追溯、可打印，并保留人工确认边界。

## 3. 方案对比
| 方案 | 优点 | 风险 |
| --- | --- | --- |
| A | 结构稳定 | 依赖浏览器 |
| B | 兼容旧环境 | 版式能力有限 |

## 4. 架构
输入经过证据登记、方案编写、PDF 渲染和独立验收。

## 5. 安全
不在报告中保存密钥、客户隐私或本机绝对路径。

## 6. 验收
逐页检查空白、裁切、字体、表格和链接。

## 7. 风险
缺少浏览器时必须明确停止或使用已声明的兼容引擎。

## 8. 最终建议
以 Playwright 为正式渲染引擎。
"""
                else:
                    body = """---
title: "Visual Baseline Plan"
subtitle: "Formal Review Draft"
language: "en-US"
version: "V2.0"
recommendation: "Use phased delivery with human approval"
---

# Visual Baseline Plan

## 1. Executive Summary
This document validates layout, color, pagination, and English typography.

## 2. Requirements
The report must be clear, traceable, printable, and subject to human approval.

## 3. Alternatives
| Option | Benefit | Risk |
| --- | --- | --- |
| A | Stable structure | Browser dependency |
| B | Legacy compatibility | Limited layout fidelity |

## 4. Architecture
Inputs pass through evidence registration, authoring, PDF rendering, and review.

## 5. Security
The report excludes secrets, customer privacy, and local absolute paths.

## 6. Acceptance
Every page is checked for blanks, clipping, fonts, tables, and links.

## 7. Risks
A missing browser must stop visibly or use a declared compatibility engine.

## 8. Final Recommendation
Use Playwright as the formal renderer.
"""
                proposal.write_text(body, encoding="utf-8")
                pdf = workspace / "output" / "pdf" / "formal-plan.pdf"
                render = subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "scripts" / "render_plan_pdf.py"),
                        str(proposal),
                        "--output",
                        str(pdf),
                        "--engine",
                        "playwright",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(render.returncode, 0, render.stdout + render.stderr)
                pages = workspace / "tmp" / "rendered-pages"
                raster = subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "scripts" / "render_pdf_pages.py"),
                        str(pdf),
                        "--output-dir",
                        str(pages),
                        "--dpi",
                        "90",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(raster.returncode, 0, raster.stdout + raster.stderr)
                visual = subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "scripts" / "check_visual_baseline.py"),
                        str(pages),
                        "--language",
                        language,
                        "--json",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(visual.returncode, 0, visual.stdout + visual.stderr)
                payload = json.loads(visual.stdout)
                self.assertEqual(payload["baseline"], baselines[language]["name"])
                self.assertEqual(payload["failures"], [])

    def test_ci_covers_required_python_versions_and_release_gates(self) -> None:
        workflow = (
            ROOT / ".github" / "workflows" / "ci.yml"
        ).read_text(encoding="utf-8")
        for version in ("3.9", "3.11", "3.13"):
            self.assertIn(version, workflow)
        self.assertIn("requirements-v2.txt", workflow)
        self.assertIn("validate_plugin_layout.py", workflow)
        self.assertIn("evaluate_router.py", workflow)
        self.assertIn("scan_sensitive_content.py", workflow)
        self.assertIn("playwright install", workflow)


if __name__ == "__main__":
    unittest.main()
