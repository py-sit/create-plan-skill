# Source register

`source-register.yaml` is the machine-readable source of truth for external and
internal references used by a proposal.

Each source uses:

- `id`: stable `S-###` identifier;
- `title`: human-readable source title;
- `kind`: `official-doc`, `repository`, `release`, `paper`, `dataset`,
  `runtime`, `project-file`, `user-provided`, or `other`;
- `url`: optional public HTTPS URL;
- `local_path`: optional workspace-relative path;
- `publisher`;
- `accessed`: ISO date;
- `version`: product version, commit, release, or document revision;
- `license`: source or repository license when relevant;
- `supports`: `E-###` evidence IDs;
- `notes`: concise limitations or provenance.

Never register a local absolute path. Store a workspace-relative path instead.
Do not copy secrets or private tokens into titles, notes, URLs, or evidence.
