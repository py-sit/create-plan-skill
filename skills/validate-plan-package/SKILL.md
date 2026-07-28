---
name: validate-plan-package
description: Use when an existing formal proposal workspace, Mermaid set, PDF, source register, or delivered package must be independently checked without rewriting it.
license: MIT
metadata:
  version: "2.0.0"
  author: "py-sit"
---

# Validate Plan Package

## Outcome

Independently determine whether a proposal package is complete, traceable,
private-path safe, visually reviewable, and identical to the delivered copy.

## Workflow

1. Do not rewrite source unless the user explicitly requests remediation.
2. Validate the mode-specific artifact set:

   ```bash
   python3 scripts/validate_plan_package.py \
     --mode full-proposal \
     --workspace /absolute/path/to/workspace
   ```

3. Check `plan-manifest.yaml` and `source-register.yaml` schema and referential
   integrity.
4. Verify evidence IDs, source IDs, decision IDs, local links, Mermaid formats,
   PDF metadata/text/page count, artifact hashes, and delivered-copy SHA256.
5. Run sensitive-content scanning. Never echo matched secret values.
6. Render every PDF page and inspect actual images. Text extraction alone does
   not prove visual quality.
7. Report each defect with the affected file, failed contract, impact, and
   remediation. Separate blocking defects from warnings.

Do not declare a package valid because a renderer exited successfully.

Read `../../shared/references/stage-contracts.md` and
`../../shared/references/pdf-quality.md`.
