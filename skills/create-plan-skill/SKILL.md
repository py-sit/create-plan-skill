---
name: create-plan-skill
description: Use when a user needs an evidence-based formal proposal, architecture recommendation, customer-facing plan, or verified proposal PDF from incomplete or complex requirements.
license: MIT
metadata:
  version: "2.0.0"
  author: "py-sit"
---

# Create Plan Router

## Purpose

Route formal-plan work to the narrowest specialist skill while preserving one
traceable package across discovery, research, authoring, and validation.

Do not expose private chain-of-thought. Record only concise artifacts that help
the user review a decision: confirmed facts, evidence, assumptions,
alternatives, decisions, risks, open questions, and verification results.

## Routing

Select exactly one primary specialist for the current turn:

| User intent | Primary skill | Stop condition |
| --- | --- | --- |
| Clarify an incomplete goal, scope, authority, or acceptance rule | `$clarify-plan-requirements` | The requested brief or next decision question is delivered |
| Research current options, GitHub projects, standards, or architecture choices | `$research-plan-options` | Evidence-backed comparison and recommendation are delivered |
| Write or update the formal proposal and create its PDF package | `$author-formal-plan` | Editable source, diagrams, PDF, and render evidence exist |
| Audit an existing plan package without rewriting it | `$validate-plan-package` | Defects and verification evidence are reported |

Use multiple specialists only when the user explicitly asks for an end-to-end
proposal. Run them in this order:

1. `$clarify-plan-requirements`
2. `$research-plan-options`
3. `$author-formal-plan`
4. `$validate-plan-package`

Do not silently advance into implementation or deployment. A formal proposal is
a decision artifact, not authorization to change code, production systems, or
data.

## Shared Contract

- Read the nearest project instructions before inspecting a repository.
- Inspect discoverable facts rather than asking the user for facts available in
  files, logs, runtime state, or referenced documents.
- Use current primary sources for changing technologies.
- Keep source and generated artifacts separate.
- Maintain `plan-manifest.yaml` and `source-register.yaml` in V2 workspaces.
- Preserve evidence IDs and decision IDs across stages.
- Never put credentials, private keys, raw secrets, or unnecessary local
  absolute paths into a proposal package.
- A completed Mermaid deliverable includes `.mmd`, `.svg`, `.png`, and `.pdf`.
- A full proposal is incomplete until every PDF page has been rendered and
  visually inspected.

## Compatibility

The repository root keeps the V1.1 standalone skill and CLI contract for
existing installations. New plugin installs use the skills under `skills/`.
V1.1 workspaces can be upgraded with:

```bash
python3 scripts/migrate_v11_workspace.py /absolute/path/to/workspace --apply
```
