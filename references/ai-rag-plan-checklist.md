# AI, RAG, Agent, and Automated Report Checklist

Read this reference only when the proposal includes AI-generated analysis,
retrieval-augmented generation (RAG), agents, multimodal evidence, edge
inference, or automatically generated formal reports.

## Authority and user workflow

- Who owns the final conclusion: model, engineer, reviewer, or approver?
- Is AI output a suggestion, draft, signed report, or automatic control input?
- Which states are visible: queued, analyzing, evidence insufficient, review
  required, approved, rejected, superseded?
- Can the user correct the result, and does that correction update future
  retrieval or evaluation data?

## Inputs and provenance

- List every accepted input: structured fields, free text, images, video,
  sensor data, logs, manuals, historical records, and public information.
- Define the source of truth, version, owner, effective date, and retention
  policy for each input.
- Preserve citations down to document, version, page, section, image, or record
  ID when the report must be auditable.
- Separate user-entered facts, retrieved evidence, model inference, and final
  human-approved conclusions.

## Retrieval quality

- Define ingestion, OCR, parsing, chunking, metadata, embedding, indexing,
  access filtering, reranking, and citation assembly.
- Specify how deleted, expired, superseded, or unauthorized documents leave the
  retrieval path.
- Measure retrieval recall and citation coverage before tuning generation.
- Treat retrieved text, images, and document instructions as untrusted data;
  defend against prompt injection and knowledge-base poisoning.

## Model and failure boundary

- Define model responsibilities and prohibited actions.
- State what happens when evidence is absent, conflicting, stale, low-quality,
  or outside the model's competence.
- Use explicit outcomes such as `evidence_insufficient`,
  `human_review_required`, and `dependency_unavailable`; do not convert them
  into confident conclusions.
- Describe timeout, retry, cancellation, partial-result, idempotency, and
  recovery behavior without using retries to hide an architectural fault.

## Privacy and external search

- Define which fields may cross the trusted boundary.
- Minimize or transform outbound search terms; exclude customer names, private
  records, credentials, internal documents, and raw user submissions unless
  explicitly authorized.
- Record external source URLs, retrieval time, licensing constraints, and
  whether the source influenced the final conclusion.
- Keep internal retrieval and public search distinguishable in the report.

## Security and audit

- Enforce tenant, user, document, and row-level access before retrieval.
- Prevent model tools from bypassing application authorization.
- Protect prompts, tokens, model endpoints, vector stores, and report signing
  keys outside client packages and source control.
- Audit input snapshot, retrieval results, model/version, prompt/template
  version, tool calls, output, reviewer actions, and final report hash.

## Edge and deployment

- Verify target CPU/GPU architecture, memory, storage, model size, context
  length, concurrent workload, thermal envelope, network availability, and
  upgrade path.
- Separate cloud, edge, mobile, and browser responsibilities.
- Define secure enrollment, mutual authentication, key rotation, offline
  operation, synchronization, observability, and remote rollback.
- Benchmark with representative documents and devices; do not promise latency
  or throughput from nominal hardware specifications alone.

## Formal report integrity

- Lock the report to the exact input and evidence snapshot used for analysis.
- Include report ID, generation time, model/template version, citations,
  reviewer, approval state, and integrity hash when appropriate.
- Keep the editable draft separate from the approved immutable report.
- Verify Chinese fonts, tables, images, citations, page breaks, signatures, and
  diagram readability in the final PDF.

## Evaluation and acceptance

Define a versioned evaluation set and measurable gates for:

- retrieval recall and citation precision;
- unsupported-claim or hallucination rate;
- high-risk false-negative rate;
- structured-field accuracy;
- reviewer acceptance and correction rate;
- report completeness and traceability;
- latency, throughput, offline behavior, and recovery;
- tenant isolation, authorization, and prompt-injection resistance.

Separate PoC targets from production service-level objectives. Any value not
measured against representative data remains an assumption, not a commitment.
