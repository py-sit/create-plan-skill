# Discovery and Q&A

## Goal

Turn incomplete language into a confirmed decision brief without forcing the user to become a technical analyst.

## Evidence-first discovery

Before asking questions, inspect:

- project instructions and repository structure;
- existing user flows and product screens;
- schemas, APIs, logs, runtime behavior, and deployment topology;
- supplied files, templates, images, spreadsheets, and PDFs;
- prior confirmed decisions in the active conversation.

Do not ask “what technology is used?” when the repository answers it. Ask only questions that require user authority.

## One-question sequence

Ask at most one user-visible decision question per turn. A short list of
identified gaps may precede it, but do not phrase every gap as a separate
question. Write gaps as declarative labels or statements; only one sentence or
choice block may require a user response. Use this order and stop once
sufficient:

1. **Outcome** - What decision or action must the proposal enable?
2. **Audience** - Who reviews, operates, or approves it?
3. **Workflow** - Where does the new capability enter the current process?
4. **Authority** - What may the system automate, and what requires human confirmation?
5. **Inputs** - Which data, documents, images, or system records are authoritative?
6. **Outputs** - What exact report, page, API, file, notification, or status is required?
7. **Privacy** - What information may leave the trusted boundary?
8. **Deployment** - Cloud, local, edge, mobile, offline, or hybrid?
9. **Failure** - What must happen if the dependency is unavailable?
10. **Acceptance** - What observable result proves the phase is successful?

For AI-generated formal reports, confirm report authority and accountability
before model or RAG architecture: internal advice, editable draft,
human-approved record, or externally authoritative document are different
products with different audit and safety boundaries.

## Good questions

- “AI结果需要工程师确认后才能提交，还是仅供查看？”
- “公开搜索允许发送哪些字段，哪些内容禁止外发？”
- “报告是一条记录一份，还是一个周期汇总一份？”
- “AI不可用时必须阻止提交，还是允许带明确提示的人工提交？”

## Poor questions

- “你想怎么做？” - too broad.
- “要不要安全？” - no useful trade-off.
- “数据库是什么？” - discoverable from the project.
- Five unrelated questions in one message - causes partial answers and hidden assumptions.

## Confirmed brief

Before design, summarize:

- problem;
- primary user;
- trigger;
- required result;
- authority boundary;
- data boundary;
- deployment constraint;
- acceptance criteria;
- non-goals.

Ask the user to correct material misunderstandings, not to rewrite the brief.

## When to stop asking

Stop when:

- the remaining choices can be safely deferred to PoC measurements;
- the answer is discoverable;
- the choice does not affect architecture or acceptance;
- the user explicitly asks to use best judgment and risk is low;
- prior confirmed conversation already provides the answer.

## Mode boundaries

- In **discovery-only** mode, finish with the confirmed brief, remaining gaps,
  and at most one next question.
- In **research-and-options** mode, discovery ends when the unresolved items can
  be stated as explicit assumptions or PoC measurements.
- In **full-proposal** mode, obtain confirmation of the material brief before
  formal architecture and PDF production.
- Do not silently advance to implementation, deployment, or production data
  changes from any document mode.
