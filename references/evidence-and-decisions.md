# Evidence and Decision Records

## Evidence labels

Use these labels consistently:

| Label | Meaning |
| --- | --- |
| Confirmed requirement | Explicitly approved by the user |
| Runtime evidence | Observed behavior, logs, traffic, or live state |
| Source evidence | Current code, schema, configuration, or active assets |
| External fact | Official documentation or primary upstream source |
| Inference | A conclusion derived from cited evidence |
| Assumption | A temporary choice requiring validation |
| Decision | Selected option and rationale |
| Open question | A decision that must remain unresolved |

Never present an assumption as confirmed.

`Confirmed requirement` records user authority about desired behavior.
`Runtime evidence` and `Source evidence` record observed current behavior; they
do not become requirements unless the user or governing specification adopts
them.

## Evidence register

Record:

| ID | Claim | Label | Source | Freshness | Impact |
| --- | --- | --- | --- | --- | --- |
| E-001 | Example claim | Source evidence | file/path:line | Current checkout | Architecture |

For live or changing facts, include the observation date.

## Option comparison

Compare real alternatives using weighted decision criteria:

| Criterion | Weight | Option A | Option B | Option C |
| --- | ---: | ---: | ---: | ---: |
| Workflow fit | 25 |  |  |  |
| Security boundary | 20 |  |  |  |
| Existing-system reuse | 15 |  |  |  |
| Implementation complexity | 15 |  |  |  |
| Operating complexity | 10 |  |  |  |
| Platform compatibility | 10 |  |  |  |
| Lock-in | 5 |  |  |  |

Weights are adjustable. Explain decisive differences rather than relying only on totals.

## Decision record

For each material decision record:

- **Decision**:
- **Status**: proposed / approved / superseded
- **Context**:
- **Options considered**:
- **Selected option**:
- **Why**:
- **Trade-offs**:
- **Failure boundary**:
- **Rollback or exit strategy**:
- **Validation needed**:

## Reasoning transparency

Provide concise decision rationale. Do not dump internal monologue, token-by-token reasoning, or speculative scratch work.

A useful rationale states:

1. evidence;
2. constraint;
3. alternatives;
4. decision criterion;
5. selected option;
6. remaining uncertainty.
