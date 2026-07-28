---
name: clarify-plan-requirements
description: Use when a formal proposal request has unresolved business goals, users, scope, authority boundaries, inputs, outputs, risks, or acceptance criteria.
license: MIT
metadata:
  version: "2.0.0"
  author: "py-sit"
---

# Clarify Plan Requirements

## Outcome

Produce a confirmed, reviewable requirement brief without prematurely choosing
technology or authoring the final proposal.

## Workflow

1. Read available files, screenshots, prior decisions, project instructions,
   and runtime evidence before asking questions.
2. Reconstruct:
   - target users and audience;
   - current problem and desired workflow;
   - required inputs and outputs;
   - authority and human-approval boundaries;
   - privacy, security, and production boundaries;
   - measurable acceptance criteria;
   - explicit non-goals.
3. Separate confirmed facts, inferences, assumptions, and open decisions.
4. Ask at most one decision-driving question per user-visible turn.
5. Stop when the requested brief or next question is complete. Do not begin
   external research, PDF authoring, implementation, or deployment unless the
   user expands the scope.

For formal AI-generated, audit, safety, regulatory, or signed reports, confirm
who owns the conclusion, who approves it, how evidence and revisions are
preserved, and what is shown when evidence is insufficient.

## Artifact Contract

Update:

- `brief.md`
- `questions.md`
- `plan-manifest.yaml`

Keep stable IDs such as `Q-001`. Mark assumptions explicitly and never present
them as confirmed facts.

Read `../../shared/references/stage-contracts.md` for handoff requirements.
