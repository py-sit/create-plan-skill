#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Dict, List, Tuple

from validate_evals import MODE_TO_SKILL, validate_cases


DEFAULT_THRESHOLD = 0.95

DISCOVERY_PATTERNS = (
    r"\bclarif(?:y|ication)\b",
    r"\bmissing requirements?\b",
    r"\bquestions? first\b",
    r"\bask me\b",
    r"\bbefore (?:writing|proposing|designing)\b",
    r"\bdo not (?:research|write|create)\b",
    r"\bdon't (?:research|write|create)\b",
    r"先(?:不要|别|只)?(?:问|澄清|确认)",
    r"只问",
    r"澄清",
    r"需求缺口",
    r"补齐需求",
    r"确认(?:责任|审批|范围|验收|输入|输出)",
    r"别急着出方案",
)

VALIDATION_ACTION_PATTERNS = (
    r"\baudit\b",
    r"\bvalidate\b",
    r"\bverify\b",
    r"\binspect\b",
    r"\breview (?:the )?existing\b",
    r"核验",
    r"验证",
    r"审计",
    r"验收",
    r"检查",
)

VALIDATION_ARTIFACT_PATTERNS = (
    r"\bproposal package\b",
    r"\bplan package\b",
    r"\bexisting proposal\b",
    r"\bsource register\b",
    r"\bevidence register\b",
    r"\bmermaid\b",
    r"\bpdf hash\b",
    r"\bsha-?256\b",
    r"\bpage clipping\b",
    r"\bdelivered pdf\b",
    r"方案包",
    r"现有方案",
    r"证据登记",
    r"来源登记",
    r"mermaid",
    r"pdf.{0,12}(?:哈希|裁切|空白|分页)",
    r"交付.{0,8}pdf",
)

RESEARCH_ACTION_PATTERNS = (
    r"\bresearch\b",
    r"\bcompare\b",
    r"\bevaluate\b",
    r"\bevaluate (?:the )?(?:options|alternatives)\b",
    r"\boption research\b",
    r"\btechnology selection\b",
    r"\bstudy\b",
    r"研究",
    r"调研",
    r"比较",
    r"选型",
    r"方案对比",
)

RESEARCH_CONTEXT_PATTERNS = (
    r"\barchitecture\b",
    r"\bdeployment\b",
    r"\bsecurity\b",
    r"\bprivacy\b",
    r"\brag\b",
    r"\bllm\b",
    r"\bai\b",
    r"\bedge (?:device|computer|deployment)\b",
    r"\bsolution\b",
    r"\bformal proposal\b",
    r"架构",
    r"部署",
    r"安全",
    r"隐私",
    r"rag",
    r"大模型",
    r"边缘设备",
    r"联网搜索",
    r"正式方案",
)

RESEARCH_STOP_PATTERNS = (
    r"\bno (?:formal )?pdf\b",
    r"\bwithout (?:a )?(?:formal )?(?:proposal|pdf)\b",
    r"\bdo not (?:write|create|generate).{0,20}(?:proposal|pdf)\b",
    r"\bdon't (?:write|create|generate).{0,20}(?:proposal|pdf)\b",
    r"不要.{0,12}(?:正式方案|pdf)",
    r"先不要.{0,12}(?:写方案|生成pdf)",
    r"只(?:做|给).{0,8}(?:研究|调研|比较|选型)",
)

FULL_PROPOSAL_PATTERNS = (
    r"\bformal proposal\b",
    r"\bproposal pdf\b",
    r"\bpdf proposal\b",
    r"\bcustomer-facing proposal\b",
    r"\bexecutive proposal\b",
    r"\bboard-ready proposal\b",
    r"\barchitecture proposal\b",
    r"\bformal (?:architecture|security|deployment|solution) plan\b",
    r"\bcreate.{0,30}(?:formal proposal|proposal pdf|pdf proposal)\b",
    r"\bgenerate.{0,30}(?:formal proposal|proposal pdf|pdf proposal)\b",
    r"正式方案",
    r"方案.{0,8}pdf",
    r"pdf.{0,8}方案",
    r"生成.{0,8}pdf",
    r"客户(?:评审|汇报).{0,8}方案",
    r"面向客户.{0,8}方案",
    r"管理层.{0,8}方案",
)


def matches_any(text: str, patterns: Tuple[str, ...]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def classify_prompt(prompt: str) -> Tuple[str, str]:
    text = " ".join(prompt.strip().split()).lower()

    if (
        matches_any(text, VALIDATION_ACTION_PATTERNS)
        and matches_any(text, VALIDATION_ARTIFACT_PATTERNS)
    ):
        mode = "validation-only"
    elif matches_any(text, DISCOVERY_PATTERNS):
        mode = "discovery-only"
    else:
        asks_for_research = (
            matches_any(text, RESEARCH_ACTION_PATTERNS)
            and matches_any(text, RESEARCH_CONTEXT_PATTERNS)
        )
        explicitly_stops_before_proposal = matches_any(
            text,
            RESEARCH_STOP_PATTERNS,
        )
        asks_for_full_proposal = matches_any(text, FULL_PROPOSAL_PATTERNS)

        if asks_for_research and explicitly_stops_before_proposal:
            mode = "research-and-options"
        elif asks_for_full_proposal:
            mode = "full-proposal"
        elif asks_for_research:
            mode = "research-and-options"
        else:
            mode = "none"

    return mode, MODE_TO_SKILL[mode]


def safe_ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 1.0
    return numerator / denominator


def evaluate_cases(
    cases: List[Dict[str, object]],
    threshold: float,
) -> Tuple[Dict[str, object], bool]:
    true_positive = 0
    false_positive = 0
    false_negative = 0
    true_negative = 0
    correct_modes = 0
    correct_skills = 0
    mismatches: List[Dict[str, object]] = []

    for case in cases:
        expected_mode = str(case["expected_mode"])
        expected_skill = str(case["expected_skill"])
        expected_trigger = case["should_trigger"] is True
        predicted_mode, predicted_skill = classify_prompt(str(case["prompt"]))
        predicted_trigger = predicted_mode != "none"

        if predicted_trigger and expected_trigger:
            true_positive += 1
        elif predicted_trigger and not expected_trigger:
            false_positive += 1
        elif not predicted_trigger and expected_trigger:
            false_negative += 1
        else:
            true_negative += 1

        mode_matches = predicted_mode == expected_mode
        skill_matches = predicted_skill == expected_skill
        correct_modes += int(mode_matches)
        correct_skills += int(skill_matches)
        if not mode_matches or not skill_matches:
            mismatches.append(
                {
                    "id": case["id"],
                    "expected_mode": expected_mode,
                    "predicted_mode": predicted_mode,
                    "expected_skill": expected_skill,
                    "predicted_skill": predicted_skill,
                }
            )

    trigger_precision = safe_ratio(
        true_positive,
        true_positive + false_positive,
    )
    trigger_recall = safe_ratio(
        true_positive,
        true_positive + false_negative,
    )
    mode_accuracy = safe_ratio(correct_modes, len(cases))
    skill_accuracy = safe_ratio(correct_skills, len(cases))
    payload: Dict[str, object] = {
        "cases": len(cases),
        "threshold": threshold,
        "trigger_precision": round(trigger_precision, 6),
        "trigger_recall": round(trigger_recall, 6),
        "mode_accuracy": round(mode_accuracy, 6),
        "skill_accuracy": round(skill_accuracy, 6),
        "confusion_matrix": {
            "true_positive": true_positive,
            "false_positive": false_positive,
            "false_negative": false_negative,
            "true_negative": true_negative,
        },
        "mismatches": mismatches,
    }
    passed = all(
        score >= threshold
        for score in (
            trigger_precision,
            trigger_recall,
            mode_accuracy,
            skill_accuracy,
        )
    )
    payload["passed"] = passed
    return payload, passed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate the V2 create-plan router against JSONL cases."
    )
    parser.add_argument("cases", type=Path)
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help="Minimum accepted score for every routing metric.",
    )
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not 0.0 <= args.threshold <= 1.0:
        print("ERROR: --threshold must be between 0 and 1", file=sys.stderr)
        return 2

    path = args.cases.expanduser().resolve()
    if not path.is_file():
        print(f"ERROR: eval cases not found: {path}", file=sys.stderr)
        return 1

    cases, failures = validate_cases(path, profile="v2")
    if failures:
        payload = {
            "cases": len(cases),
            "validation_failures": failures,
            "passed": False,
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            for failure in failures:
                print(f"FAIL {failure}")
            print(f"failures={len(failures)}")
        return 1

    payload, passed = evaluate_cases(cases, threshold=args.threshold)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"cases={payload['cases']}")
        print(f"trigger_precision={payload['trigger_precision']:.6f}")
        print(f"trigger_recall={payload['trigger_recall']:.6f}")
        print(f"mode_accuracy={payload['mode_accuracy']:.6f}")
        print(f"skill_accuracy={payload['skill_accuracy']:.6f}")
        for mismatch in payload["mismatches"]:
            print(
                "MISMATCH "
                f"{mismatch['id']}: "
                f"mode={mismatch['predicted_mode']} "
                f"skill={mismatch['predicted_skill']}"
            )
        print(f"passed={str(passed).lower()}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
