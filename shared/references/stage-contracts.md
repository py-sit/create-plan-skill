# Stage contracts

## Discovery handoff

- `brief.md` identifies outcome, audience, current problem, workflow, inputs,
  outputs, authority, privacy/security, acceptance, and non-goals.
- `questions.md` uses stable `Q-###` identifiers.
- Material unknowns are explicit and do not masquerade as facts.

## Research handoff

- Every material external source has an `S-###` record.
- Every important claim has an `E-###` record and identifies supporting source
  IDs.
- Every material choice has a `D-###` decision record with alternatives,
  trade-offs, failure boundary, rollback, and validation needs.

## Authoring handoff

- `proposal.md` references evidence IDs and source IDs.
- Every Mermaid source has PNG, SVG, and PDF renders.
- The PDF render engine and theme are recorded in `plan-manifest.yaml`.
- Generated artifacts stay under `output/` or `diagrams/rendered/`.

## Validation handoff

- Schema and referential-integrity checks pass.
- Sensitive-content scan passes without exposing matched secret values.
- Every PDF page has a rendered image and visual-review status.
- Delivered PDF hash matches the reviewed PDF hash.
