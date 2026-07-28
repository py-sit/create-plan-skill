---
name: research-plan-options
description: Use when a formal proposal needs current primary-source research, GitHub project comparison, architecture alternatives, or an evidence-backed recommendation.
license: MIT
metadata:
  version: "2.0.0"
  author: "py-sit"
---

# Research Plan Options

## Outcome

Produce a traceable comparison of viable options and a recommendation whose
claims can be checked against registered sources.

## Workflow

1. Read `brief.md`, unresolved questions, and the current
   `source-register.yaml`.
2. Prefer primary sources:
   - official documentation for APIs, platforms, standards, hardware, and
     security behavior;
   - original repositories and release pages for open-source projects;
   - project source, runtime evidence, and supplied documents for current-state
     claims.
3. Register each material source with an `S-###` ID, access date, version or
   revision when available, license when relevant, and the claims it supports.
4. Distinguish verified facts from architectural inference.
5. Compare at least two credible options for each material decision using:
   workflow fit, reuse, implementation and operating complexity, ownership,
   security, platform fit, lock-in, failure isolation, and phased cost.
6. Record the recommendation and rejected alternatives in `decision-log.md`.
7. Stop after the requested research and recommendation. Do not force PDF
   production or implementation.

Never use repository popularity as the sole architecture criterion. Do not
quote a source beyond its license or copyright boundary.

## Artifact Contract

Update:

- `evidence-register.md`
- `source-register.yaml`
- `decision-log.md`
- `plan-manifest.yaml`

Use `E-###`, `S-###`, and `D-###` identifiers consistently.

Read `../../shared/references/source-register.md` and
`../../shared/references/stage-contracts.md`.
