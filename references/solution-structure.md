# Formal Solution Structure

Use only sections relevant to the task, while preserving a clear decision narrative.

## Recommended structure

1. **Cover**
   - title, subtitle, status, version, date, scope boundary.
2. **Executive summary**
   - problem, proposed solution, business result, critical constraints.
3. **Business background**
   - current workflow, reusable capabilities, pain points.
4. **Confirmed requirements**
   - numbered, testable, free of implementation ambiguity.
5. **Goals and non-goals**
6. **Alternative comparison**
   - two or three viable approaches and recommendation.
7. **Recommended architecture**
   - responsibilities, boundaries, ownership, dependencies.
8. **User workflow**
   - trigger, progress, confirmation, completion, rejection paths.
9. **Data and processing flow**
   - inputs, snapshots, transformations, persistence, outputs.
10. **Interfaces and data model**
11. **Permission and audit model**
12. **Security and privacy**
13. **Failure semantics**
   - unavailable, timeout, partial, conflict, retry, recovery.
14. **Observability and operations**
15. **Testing and acceptance**
16. **Phased rollout**
17. **Open-source or vendor reference list**
18. **Risks and mitigations**
19. **Parameters to confirm during PoC**
20. **Final recommendation**

## Writing rules

- Use customer language for business sections and technical precision for architecture sections.
- Explain acronyms on first use.
- Distinguish “must”, “should”, “may”, and “not included”.
- Keep historical data and future behavior separate.
- State whether changes are additive, destructive, reversible, or migration-dependent.
- Give every failure state a user-visible meaning and an operator-visible signal.
- Do not promise performance before measurement. Define the benchmark method instead.
- Place detailed citations, versions, hashes, and audit fields in appendices when they would overload the main report.

## Diagram selection

| Question | Diagram |
| --- | --- |
| What components exist? | Architecture flowchart |
| Who calls whom and in what order? | Sequence diagram |
| How does status change? | State diagram |
| Who owns each responsibility? | Swimlane or responsibility map |
| What is delivered by phase? | Roadmap flowchart |

Each diagram must have:

- one clear purpose;
- readable labels at A4 scale;
- source `.mmd`;
- rendered PNG, SVG, and PDF;
- a caption in the proposal.

Prefer a landscape or balanced layout for diagrams embedded in portrait A4
reports. A very tall, narrow flowchart can be technically correct but still be
too small to read at normal review zoom.
