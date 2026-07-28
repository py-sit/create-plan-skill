---
name: author-formal-plan
description: Use when confirmed requirements and evidence must be turned into a structured customer-facing proposal, Mermaid diagrams, and a polished PDF package.
license: MIT
metadata:
  version: "2.0.0"
  author: "py-sit"
---

# Author Formal Plan

## Outcome

Create editable proposal source, traceable diagrams, and a polished PDF without
inventing missing evidence or authorizing implementation.

## Workflow

1. Require a usable brief and decision record. If a missing answer materially
   changes scope, return to `$clarify-plan-requirements`.
2. Confirm that material claims have evidence/source IDs. If not, return to
   `$research-plan-options`.
3. Initialize or update the workspace:

   ```bash
   python3 scripts/init_plan_workspace.py \
     --output-dir /absolute/path/to/workspace \
     --title "Plan title" \
     --language zh-CN
   ```

4. Author `proposal.md` with explicit boundaries for confirmed facts,
   recommendations, PoC measurements, later decisions, non-goals, data safety,
   failure behavior, rollout gates, rollback, and acceptance.
5. Create Mermaid source and render each diagram to `.svg`, `.png`, and `.pdf`.
6. Render the proposal with the Playwright engine:

   ```bash
   python3 scripts/render_plan_pdf.py proposal.md \
     --output output/pdf/formal-plan.pdf \
     --engine playwright
   ```

7. If Playwright is unavailable, use `--engine reportlab` only as a visible,
   recorded fallback. Do not silently call it the primary result.
8. Render every PDF page and inspect it for clipping, blank pages, unreadable
   tables, broken diagrams, missing glyphs, and accidental private paths.

## Artifact Contract

Update `plan-manifest.yaml` with theme, render engine, artifact paths, hashes,
and stage status. Keep editable source outside `output/`.

Read:

- `../../shared/references/stage-contracts.md`
- `../../shared/references/source-register.md`
- `../../shared/references/pdf-quality.md`
