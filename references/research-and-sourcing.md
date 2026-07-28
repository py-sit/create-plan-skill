# Research and Sourcing

## Source priority

1. live runtime evidence;
2. actively served assets and current configuration;
3. official product documentation;
4. primary source repositories, specifications, and research papers;
5. high-quality secondary analysis;
6. community discussion as supporting evidence only.

## Official documentation

For libraries, SDKs, APIs, cloud services, hardware, and standards:

- check the current version and publication date;
- use official documentation or primary repositories;
- verify platform and architecture support;
- distinguish stable features from experimental features;
- record security and licensing constraints;
- avoid making version-sensitive claims from memory.

## GitHub evaluation

For every referenced repository record:

- repository owner and project name;
- intended role;
- license;
- latest release or recent maintenance activity;
- supported platforms and CPU architecture;
- deployment model;
- dependencies and resource footprint;
- security boundary;
- integration fit;
- recommendation: adopt / evaluate / reference only / reject.

Stars are not an architecture criterion.

## Reuse decision

Prefer an existing project when it:

- solves the same responsibility boundary;
- supports the target platform;
- has acceptable license and maintenance;
- can be isolated behind a stable interface;
- does not duplicate the business source of truth;
- can be observed, upgraded, and replaced.

Reject or use only as reference when it:

- takes ownership of users, permissions, or business data already owned elsewhere;
- requires exposing sensitive services;
- is incompatible with the target architecture;
- hides important state transitions;
- creates excessive operating complexity for current scale.

## Citation discipline

- Cite the claim near the relevant paragraph.
- Do not cite irrelevant sources merely to increase citation count.
- Mark architectural conclusions as inference.
- Avoid large verbatim extracts.
- Keep a compact source table in the proposal or appendix.
