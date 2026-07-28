#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Dict, List, Set


MODES = {
    "discovery-only",
    "research-and-options",
    "full-proposal",
    "validation-only",
    "none",
}

REQUIRED_FIELDS = {
    "id",
    "prompt",
    "should_trigger",
    "expected_mode",
    "expected_behaviors",
    "forbidden_behaviors",
}

V2_REQUIRED_FIELDS = {
    "expected_skill",
    "locale",
    "category",
}

EXPECTED_SKILLS = {
    "clarify-plan-requirements",
    "research-plan-options",
    "author-formal-plan",
    "validate-plan-package",
    "none",
}

LOCALES = {
    "zh-CN",
    "en-US",
}

MODE_TO_SKILL = {
    "discovery-only": "clarify-plan-requirements",
    "research-and-options": "research-plan-options",
    "full-proposal": "author-formal-plan",
    "validation-only": "validate-plan-package",
    "none": "none",
}

CATEGORY_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")


def validate_cases(
    path: Path,
    profile: str = "v1",
) -> tuple[List[Dict[str, object]], List[str]]:
    failures: List[str] = []
    cases: List[Dict[str, object]] = []
    seen_ids: Set[str] = set()
    required_fields = set(REQUIRED_FIELDS)
    if profile == "v2":
        required_fields.update(V2_REQUIRED_FIELDS)

    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            case = json.loads(line)
        except json.JSONDecodeError as error:
            failures.append(f"line {line_number}: invalid JSON: {error}")
            continue
        if not isinstance(case, dict):
            failures.append(f"line {line_number}: case must be an object")
            continue
        missing = sorted(required_fields - set(case))
        if missing:
            failures.append(f"line {line_number}: missing fields {missing}")
            continue
        case_id = case["id"]
        if not isinstance(case_id, str) or not case_id.strip():
            failures.append(f"line {line_number}: id must be a non-empty string")
        elif case_id in seen_ids:
            failures.append(f"line {line_number}: duplicate id {case_id}")
        else:
            seen_ids.add(case_id)
        if not isinstance(case["prompt"], str) or not case["prompt"].strip():
            failures.append(f"{case_id}: prompt must be a non-empty string")
        if not isinstance(case["should_trigger"], bool):
            failures.append(f"{case_id}: should_trigger must be boolean")
        expected_mode_value = case["expected_mode"]
        if (
            not isinstance(expected_mode_value, str)
            or expected_mode_value not in MODES
        ):
            failures.append(
                f"{case_id}: invalid expected_mode {expected_mode_value}"
            )
        for field in ("expected_behaviors", "forbidden_behaviors"):
            value = case[field]
            if (
                not isinstance(value, list)
                or not value
                or not all(isinstance(item, str) and item.strip() for item in value)
            ):
                failures.append(f"{case_id}: {field} must be a non-empty string list")

        if profile == "v2":
            expected_skill = case["expected_skill"]
            if (
                not isinstance(expected_skill, str)
                or expected_skill not in EXPECTED_SKILLS
            ):
                failures.append(
                    f"{case_id}: invalid expected_skill {expected_skill}"
                )

            locale = case["locale"]
            if not isinstance(locale, str) or locale not in LOCALES:
                failures.append(f"{case_id}: invalid locale {locale}")

            category = case["category"]
            if (
                not isinstance(category, str)
                or not CATEGORY_PATTERN.fullmatch(category)
            ):
                failures.append(
                    f"{case_id}: category must be a non-empty kebab-case string"
                )

            expected_mode = case["expected_mode"]
            mapped_skill = (
                MODE_TO_SKILL.get(expected_mode)
                if isinstance(expected_mode, str)
                else None
            )
            if mapped_skill is not None and expected_skill != mapped_skill:
                failures.append(
                    f"{case_id}: expected_skill {expected_skill} does not match "
                    f"expected_mode {expected_mode}"
                )

            should_trigger = case["should_trigger"]
            if should_trigger is False and (
                expected_mode != "none" or expected_skill != "none"
            ):
                failures.append(
                    f"{case_id}: non-trigger cases must use mode and skill none"
                )
            if should_trigger is True and (
                expected_mode == "none" or expected_skill == "none"
            ):
                failures.append(
                    f"{case_id}: trigger cases must select a specialist mode and skill"
                )
        cases.append(case)

    if profile == "v1":
        if not 12 <= len(cases) <= 20:
            failures.append(f"suite: expected 12-20 cases, found {len(cases)}")
    elif len(cases) < 30:
        failures.append(f"suite: expected at least 30 cases, found {len(cases)}")

    triggers = {case.get("should_trigger") for case in cases}
    if triggers != {True, False}:
        failures.append("suite: must contain both trigger and non-trigger cases")
    expected_trigger_modes = {
        "discovery-only",
        "research-and-options",
        "full-proposal",
        "validation-only",
    }
    actual_modes = {
        str(case.get("expected_mode"))
        for case in cases
        if case.get("should_trigger") is True
    }
    missing_modes = sorted(expected_trigger_modes - actual_modes)
    if missing_modes:
        failures.append(f"suite: missing triggered modes {missing_modes}")

    if profile == "v2":
        actual_locales = {
            str(case.get("locale"))
            for case in cases
            if case.get("locale") in LOCALES
        }
        missing_locales = sorted(LOCALES - actual_locales)
        if missing_locales:
            failures.append(f"suite: missing locales {missing_locales}")

        non_trigger_cases = [
            case for case in cases if case.get("should_trigger") is False
        ]
        if len(non_trigger_cases) < 4:
            failures.append(
                "suite: expected at least 4 non-trigger boundary cases"
            )

        triggered_skills = {
            str(case.get("expected_skill"))
            for case in cases
            if case.get("should_trigger") is True
        }
        missing_skills = sorted((EXPECTED_SKILLS - {"none"}) - triggered_skills)
        if missing_skills:
            failures.append(
                f"suite: missing triggered specialist skills {missing_skills}"
            )
    return cases, failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate create-plan-skill JSONL eval cases."
    )
    parser.add_argument("cases", type=Path)
    parser.add_argument(
        "--profile",
        choices=("v1", "v2"),
        default="v1",
        help="Validation contract. Defaults to the V1 12-20 case contract.",
    )
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = args.cases.expanduser().resolve()
    if not path.is_file():
        print(f"ERROR: eval cases not found: {path}", file=sys.stderr)
        return 1
    cases, failures = validate_cases(path, profile=args.profile)
    payload = {
        "profile": args.profile,
        "cases": len(cases),
        "trigger_cases": sum(case["should_trigger"] is True for case in cases),
        "non_trigger_cases": sum(case["should_trigger"] is False for case in cases),
        "failures": failures,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"cases={payload['cases']}")
        print(f"trigger_cases={payload['trigger_cases']}")
        print(f"non_trigger_cases={payload['non_trigger_cases']}")
        for failure in failures:
            print(f"FAIL {failure}")
        print(f"failures={len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
