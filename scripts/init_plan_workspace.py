#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import re
import shutil
import sys


SKILL_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = {
    "zh-CN": SKILL_ROOT / "assets" / "formal-plan-template.zh-CN.md",
    "en-US": SKILL_ROOT / "assets" / "formal-plan-template.en-US.md",
}

LANGUAGE_ALIASES = {
    "zh": "zh-CN",
    "zh-cn": "zh-CN",
    "zh_CN": "zh-CN",
    "en": "en-US",
    "en-us": "en-US",
    "en_US": "en-US",
}


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value)
    return value.strip("-") or "formal-plan"


def write_text(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"Refusing to overwrite existing file: {path}")
    path.write_text(content, encoding="utf-8")


def normalize_language(value: str) -> str:
    if value in TEMPLATES:
        return value
    normalized = LANGUAGE_ALIASES.get(value.strip())
    if normalized:
        return normalized
    normalized = LANGUAGE_ALIASES.get(value.strip().lower())
    if normalized:
        return normalized
    raise ValueError(
        f"Unsupported language: {value}. Choose one of: {', '.join(TEMPLATES)}"
    )


def localized_scaffolds(language: str, title: str) -> dict[str, str]:
    if language == "en-US":
        return {
            "brief": f"""# {title} - Confirmed Brief

## Outcome

## Audience

## Current problem

## Trigger and workflow

## Required inputs

## Required outputs

## Authority boundary

## Privacy and security boundary

## Acceptance criteria

## Non-goals
""",
            "questions": """# Discovery Questions

| ID | Question | Why it matters | Answer | Status |
| --- | --- | --- | --- | --- |
| Q-001 |  |  |  | open |
""",
            "evidence": """# Evidence Register

| ID | Claim | Label | Source | Freshness | Impact |
| --- | --- | --- | --- | --- | --- |
| E-001 |  |  |  |  |  |
""",
            "decision": """# Decision Log

## D-001

- **Decision**:
- **Status**: proposed
- **Context**:
- **Options considered**:
- **Selected option**:
- **Why**:
- **Trade-offs**:
- **Failure boundary**:
- **Rollback or exit strategy**:
- **Validation needed**:
""",
            "diagram": """flowchart LR
    A["User action"] --> B["Business service"]
    B --> C["Data and tasks"]
    C --> D["Processing component"]
    D --> E["Formal deliverable"]
""",
            "user_flow": """flowchart LR
    A["Start"] --> B["Provide input"]
    B --> C["Review result"]
    C --> D{"Approved?"}
    D -->|Yes| E["Complete"]
    D -->|No| B
""",
        }
    return {
        "brief": f"""# {title} - 已确认需求简报

## 目标结果

## 受众

## 当前问题

## 触发条件与流程

## 必需输入

## 必需输出

## 权限与人工确认边界

## 隐私与安全边界

## 验收标准

## 非目标
""",
        "questions": """# 需求澄清问题

| ID | 问题 | 影响 | 回答 | 状态 |
| --- | --- | --- | --- | --- |
| Q-001 |  |  |  | open |
""",
        "evidence": """# 证据登记表

| ID | 结论 | 标签 | 来源 | 新鲜度 | 影响 |
| --- | --- | --- | --- | --- | --- |
| E-001 |  |  |  |  |  |
""",
        "decision": """# 决策日志

## D-001

- **决策**:
- **状态**: proposed
- **背景**:
- **已比较方案**:
- **选择方案**:
- **选择理由**:
- **取舍**:
- **故障边界**:
- **回滚或退出策略**:
- **待验证项**:
""",
        "diagram": """flowchart LR
    A["用户操作"] --> B["业务服务"]
    B --> C["数据与任务"]
    C --> D["处理组件"]
    D --> E["正式交付物"]
""",
        "user_flow": """flowchart LR
    A["开始"] --> B["提供输入"]
    B --> C["审阅结果"]
    C --> D{"是否批准？"}
    D -->|是| E["完成"]
    D -->|否| B
""",
    }


def build_workspace(
    output_dir: Path,
    title: str,
    force: bool,
    language: str = "zh-CN",
) -> None:
    language = normalize_language(language)
    output_dir.mkdir(parents=True, exist_ok=True)
    for directory in [
        output_dir / "assets",
        output_dir / "diagrams",
        output_dir / "diagrams" / "rendered",
        output_dir / "output" / "pdf",
        output_dir / "tmp" / "rendered-pages",
    ]:
        directory.mkdir(parents=True, exist_ok=True)

    proposal = TEMPLATES[language].read_text(encoding="utf-8")
    proposal = proposal.replace("<方案名称>", title)
    proposal = proposal.replace("<Plan Name>", title)
    proposal = proposal.replace("<YYYY-MM-DD>", date.today().isoformat())
    write_text(output_dir / "proposal.md", proposal, force)

    scaffolds = localized_scaffolds(language, title)
    write_text(
        output_dir / "brief.md",
        scaffolds["brief"],
        force,
    )
    write_text(
        output_dir / "questions.md",
        scaffolds["questions"],
        force,
    )
    write_text(
        output_dir / "evidence-register.md",
        scaffolds["evidence"],
        force,
    )
    write_text(
        output_dir / "decision-log.md",
        scaffolds["decision"],
        force,
    )
    write_text(
        output_dir / "diagrams" / "architecture.mmd",
        scaffolds["diagram"],
        force,
    )
    write_text(
        output_dir / "diagrams" / "user-flow.mmd",
        scaffolds["user_flow"],
        force,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a clean workspace for a formal proposal."
    )
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument(
        "--language",
        default="zh-CN",
        choices=sorted(TEMPLATES),
        help="Proposal language and PDF chrome.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite scaffold files if they already exist.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        build_workspace(
            args.output_dir.expanduser().resolve(),
            args.title,
            args.force,
            args.language,
        )
    except (FileExistsError, OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    output_dir = args.output_dir.expanduser().resolve()
    print(f"workspace={output_dir}")
    print(f"proposal={output_dir / 'proposal.md'}")
    print(f"language={args.language}")
    print(f"slug={slugify(args.title)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
