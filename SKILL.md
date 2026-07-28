---
name: create-plan-skill
description: Use when a user explicitly needs a formal, evidence-based solution proposal or proposal PDF from incomplete or complex requirements, including architecture, AI/RAG, deployment, security, roadmap, customer-review, or proposal-validation work.
license: MIT
metadata:
  version: "1.1.0"
  author: "py-sit"
  compatibility: "Python 3.9+; scripts/requirements.txt; Mermaid CLI or authorized Kroki; Unicode font; pdftoppm"
---

# Create Plan Skill

## Purpose

Convert a rough request into a reviewable and implementable formal proposal. Treat the proposal as a decision artifact, not decorative documentation.

For a full proposal, produce:

- a confirmed requirement brief;
- an evidence and assumption register;
- a decision log with alternatives and trade-offs;
- a structured Markdown proposal;
- Mermaid source plus rendered PNG, SVG, and PDF diagrams;
- a polished PDF;
- validation evidence and a concise delivery summary.

Do not expose private chain-of-thought. Record only concise, useful reasoning artifacts: evidence, assumptions, alternatives, decision criteria, rejected options, risks, and the rationale for the recommendation.

## Core Rules

1. Start from the business goal, user scenario, success criteria, and constraints.
2. Inspect discoverable facts yourself. Do not ask the user for facts available in files, code, logs, runtime state, or referenced documents.
3. Ask one decision-driving question at a time. Prefer short choices when appropriate.
4. Separate confirmed facts, runtime evidence, inferences, assumptions, decisions, and open questions.
5. In research-and-options and full-proposal modes, research current official
   documentation before relying on memory for changing technologies.
6. Use GitHub projects as implementation evidence, not as automatic architecture choices.
7. Compare at least two viable approaches for material architecture decisions.
8. Preserve user data and production boundaries. A proposal must never silently authorize implementation or destructive action.
9. Keep editable source and generated artifacts separate.
10. Match the deliverables to the requested operating mode. Do not force research,
    diagrams, or PDF production into a discovery-only task.
11. In full-proposal mode, do not declare completion until the PDF has been
    rendered and every page has been visually inspected.

## When Not to Use

Do not use this skill for:

- code implementation, debugging, or ordinary feature development;
- implementation plans written from an already approved specification;
- PDF resizing, conversion, merging, extraction, or other direct file editing;
- generic GitHub repository search or license comparison that is not supporting
  a formal solution decision or proposal.

Route those tasks to the relevant implementation, planning, PDF, or GitHub
research skill instead.

## Workflow

### 1. Select the operating mode

Infer the narrowest mode that satisfies the user:

- **discovery-only**: reconstruct the goal, list material gaps, and ask one
  decision-driving question per turn;
- **research-and-options**: in a formal solution-decision context, produce a
  confirmed brief, evidence register, source review, alternatives, and
  recommendation without requiring a formal PDF;
- **full-proposal**: run the complete workflow and deliver editable source,
  Mermaid source and renders, and a visually verified PDF;
- **validation-only**: inspect an existing proposal package and report defects
  without rewriting it unless requested.

An explicit user boundary such as “先问我”, “只评估”, “先用文字确认”, or
“不要生成 PDF” overrides the default full workflow. State the selected mode
briefly when it prevents accidental over-delivery.

Exit the current phase when its requested artifact is complete. Do not continue
from discovery into research, from research into formal authoring, or from
authoring into implementation without the user's request or prior approval.

### 2. Establish the working boundary

Read the closest project instructions, including `AGENTS.md`, repository documentation, and OpenSpec instructions when present.

Check:

- current workspace and Git state when an existing project is in scope;
- whether the task is document-only or includes implementation;
- production-data and security boundaries;
- requested output language, audience, file format, and destination;
- whether an existing template, screenshot, workbook, report, or brand asset is authoritative.

For a greenfield or document-only request, do not invent a repository/runtime
inspection requirement. If an existing repository is in scope and is dirty or
contains unrelated work, use an isolated worktree or a separate proposal
workspace.

### 3. Reconstruct the real objective

Write a one-paragraph working brief covering:

- who will use the result;
- what decision or activity the proposal must enable;
- the current problem;
- the desired future workflow;
- the acceptance condition;
- explicit exclusions.

This is a concise task summary, not hidden reasoning. Do not expose or persist
private chain-of-thought; share only the resulting confirmed brief, evidence,
assumptions, and open decisions when useful.

Read `references/discovery-and-qa.md` when the request is ambiguous, cross-functional, or likely to cause expensive rework.

### 4. Run focused discovery

Ask only questions whose answers materially change scope, architecture, risk, cost, or acceptance.
Ask at most one user-visible decision question in each turn. A compact list of
known gaps is allowed, but write those gaps as statements. Only one sentence or
choice block in the turn may require the user to answer.

Question order:

1. outcome and audience;
2. current workflow and pain;
3. required inputs and outputs;
4. authority and human-confirmation boundaries;
5. privacy, security, and deployment constraints;
6. failure behavior and fallback policy;
7. measurable acceptance criteria.

If AI will generate a formal, customer-facing, audit, regulatory, safety, or
signed report, discovery must confirm before design:

- whether the report is advisory, draft, human-signed, or independently
  authoritative;
- who is accountable for the conclusion and approval;
- how evidence, document versions, citations, revisions, and final report
  integrity are preserved;
- what user-visible state replaces a conclusion when evidence is insufficient
  or conflicting.

Stop asking when the answer is already supported by evidence or prior confirmed context.

After discovery, summarize the confirmed requirements and ask the user to correct only material misunderstandings.

In discovery-only mode, stop after the requested gap analysis, confirmed brief,
or next question. Do not start external research or create files unless asked.

### 5. Build an evidence register

Inspect project source, runtime evidence, documents, templates, screenshots, datasets, and existing capabilities.

For external research:

- use official documentation for APIs, frameworks, hardware, security, and deployment claims;
- use original GitHub repositories and release pages;
- record repository purpose, license, maintenance activity, platform compatibility, integration boundary, and adoption recommendation;
- distinguish verified facts from architectural inferences.

Read `references/research-and-sourcing.md` for the sourcing rubric.

For AI, RAG, agent, multimodal, or automated report systems, also read
`references/ai-rag-plan-checklist.md`.

### 6. Design alternatives

Create two or three credible approaches. For each, evaluate:

- fit with the user's workflow;
- reuse of existing capabilities;
- implementation complexity;
- operating complexity;
- data ownership;
- security boundary;
- hardware/platform fit;
- vendor or platform lock-in;
- failure isolation;
- phased delivery cost.

Lead with the recommended option and state why it wins. Do not present fake alternatives that are obviously unusable.

Record the decision using `references/evidence-and-decisions.md`.

In research-and-options mode, stop after the requested evidence review,
comparison, and recommendation. Do not force diagram or PDF production.

### 7. Present and approve the design

Present the proposed:

- scope;
- user workflow;
- architecture;
- data and interface boundaries;
- security model;
- failure semantics;
- testing and rollout strategy.

For a new capability or major architecture change, obtain user approval before
implementation, deployment, or a task-level execution plan that authorizes
changes. The proposal may still include a non-authorizing phased roadmap,
dependencies, estimates to validate, and acceptance gates.

If OpenSpec exists, create a proposal, design, tasks, and delta specs, then run strict validation. The formal PDF and OpenSpec must describe the same behavior.

### 8. Author the formal proposal

Use the structure in `references/solution-structure.md`. Adapt it to the task rather than mechanically forcing every heading.

Initialize a reusable workspace when helpful:

```bash
python3 scripts/init_plan_workspace.py \
  --output-dir /absolute/path/to/plan-workspace \
  --title "方案名称" \
  --language zh-CN
```

Use `--language en-US` for a fully English template and PDF chrome.

The proposal must make these boundaries explicit:

- what is confirmed;
- what is recommended;
- what remains to be measured in a PoC;
- what is outside the current phase;
- what requires a later user decision;
- what will not modify production data.

### 9. Create diagrams

Use Mermaid for architecture, sequence, lifecycle, state, and responsibility diagrams.

Keep `.mmd` source. Render every diagram to:

- `.png` for embedding in the proposal;
- `.svg` for scalable reuse;
- `.pdf` because Mermaid deliverables must include PDF form.

Prefer local Mermaid CLI:

```bash
python3 scripts/render_mermaid.py diagrams/architecture.mmd \
  --out-dir diagrams/rendered
```

Use public Kroki only for non-sensitive diagrams and only with explicit network permission:

```bash
python3 scripts/render_mermaid.py diagrams/architecture.mmd \
  --out-dir diagrams/rendered \
  --engine kroki \
  --allow-network
```

Never upload client names, internal topology, credentials, private endpoints, or confidential workflows to a public renderer.

### 10. Generate the PDF

Author from `assets/formal-plan-template.md` or an equivalent project-specific template.

Render:

```bash
python3 scripts/render_plan_pdf.py proposal.md \
  --output output/pdf/formal-plan.pdf
```

If the PDF scripts report missing Python packages:

```bash
python3 -m pip install -r scripts/requirements.txt
```

For project-specific branded reports, reuse the project's existing document/PDF pipeline when it provides better fidelity. Keep the same verification requirements.

Read `references/pdf-production.md` before final rendering.

### 11. Validate

Run the environment preflight before the first full render on a machine:

```bash
python3 scripts/check_environment.py
```

Run:

```bash
python3 scripts/validate_plan_package.py \
  --mode full-proposal \
  --workspace /absolute/path/to/plan-workspace
```

Also:

- validate OpenSpec when present;
- scan for `TODO`, `TBD`, placeholders, contradictions, and ambiguous requirements;
- verify links and local assets;
- render all PDF pages to images;
- inspect every page for clipping, overlap, missing Chinese glyphs, blank regions, unreadable diagrams, broken tables, inconsistent numbering, and poor page breaks;
- verify the delivered copy matches the reviewed file by SHA256.

Use the bundled helpers:

```bash
python3 scripts/render_pdf_pages.py output/pdf/formal-plan.pdf \
  --output-dir tmp/rendered-pages
python3 scripts/create_pdf_contact_sheet.py tmp/rendered-pages \
  --output tmp/contact-sheet.png
```

Do not rely only on text extraction or a successful PDF build.

### 12. Deliver

Report:

- outcome;
- only the artifacts required by the selected mode;
- for full-proposal mode: final PDF absolute path, source document, diagrams,
  specification paths, page count, and SHA256;
- validations run;
- decisions still awaiting user confirmation;
- Git branch/commit status;
- explicit statement that implementation or production changes were not performed unless separately authorized.

Do not push, merge, publish, deploy, or modify production systems unless the user explicitly requested those actions.

## Resource Guide

- `references/discovery-and-qa.md`: requirement reconstruction and one-question-at-a-time discovery.
- `references/evidence-and-decisions.md`: evidence labels, assumptions, option comparison, and decision records.
- `references/solution-structure.md`: adaptable formal proposal structure.
- `references/research-and-sourcing.md`: official-document and GitHub research rubric.
- `references/ai-rag-plan-checklist.md`: conditional checklist for AI, RAG,
  agent, multimodal, edge, and automated-report proposals.
- `references/pdf-production.md`: PDF generation and visual acceptance requirements.
- `assets/formal-plan-template.md`: copyable proposal source template.
- `assets/formal-plan-template.zh-CN.md`: Chinese proposal template.
- `assets/formal-plan-template.en-US.md`: English proposal template.
- `scripts/init_plan_workspace.py`: scaffold a clean proposal workspace.
- `scripts/check_environment.py`: report Python, package, renderer, font, and PDF QA capabilities.
- `scripts/render_mermaid.py`: render Mermaid to SVG, PNG, and PDF.
- `scripts/render_plan_pdf.py`: create a styled PDF from the proposal Markdown.
- `scripts/render_pdf_pages.py`: render every PDF page to PNG.
- `scripts/create_pdf_contact_sheet.py`: create a visual QA contact sheet.
- `scripts/validate_plan_package.py`: validate proposal source, diagrams, and PDF.
- `scripts/validate_evals.py`: validate the versioned trigger and workflow eval suite.

## Trigger Examples

- “先完整理解需求，再给我做一份正式技术方案PDF。”
- “问清楚需求后去GitHub找成熟项目，比较后输出方案。”
- “把这套AI/RAG功能整理成正式报告，并画架构图。”
- “给客户做一份产品实施方案，PDF放到桌面。”
- “Create a formal architecture proposal with evidence, diagrams, risks, and rollout phases.”
