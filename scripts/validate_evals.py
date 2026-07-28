#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Dict, List


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


def validate_cases(path: Path) -> tuple[List[Dict[str, object]], List[str]]:
    failures: List[str] = []
    cases: List[Dict[str, object]] = []
    seen_ids: set[str] = set()
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
        missing = sorted(REQUIRED_FIELDS - set(case))
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
        if case["expected_mode"] not in MODES:
            failures.append(f"{case_id}: invalid expected_mode {case['expected_mode']}")
        for field in ("expected_behaviors", "forbidden_behaviors"):
            value = case[field]
            if (
                not isinstance(value, list)
                or not value
                or not all(isinstance(item, str) and item.strip() for item in value)
            ):
                failures.append(f"{case_id}: {field} must be a non-empty string list")
        cases.append(case)

    if not 12 <= len(cases) <= 20:
        failures.append(f"suite: expected 12-20 cases, found {len(cases)}")
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
    return cases, failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate create-plan-skill JSONL eval cases."
    )
    parser.add_argument("cases", type=Path)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = args.cases.expanduser().resolve()
    if not path.is_file():
        print(f"ERROR: eval cases not found: {path}", file=sys.stderr)
        return 1
    cases, failures = validate_cases(path)
    payload = {
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
