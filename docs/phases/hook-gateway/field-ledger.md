# Input ledger (provisional pending supported CLI schema verification)

- hook_event_name: required nonempty string at gateway; exact CLI match; empty/null/type mismatch fail.
- session_id: required nonempty string for supported adapter; common validation; no coercion.
- cwd: required absolute string; retained metadata; no root fallback.
- prompt: required string for UserPromptSubmit; empty valid; event dispatcher.
- transcript_path: optional metadata pending schema verification; when present nonempty string; never read here.
- permission_mode: optional metadata pending schema verification; when present nonempty string; no enum guessing.
- Unknown properties: retained unchanged; not forwarded to LAYA.
- project_root: explicit application configuration, never guessed from cwd; feature prerequisite.

Outcomes and exhaustive flow reason mapping will be documented after feature adapter inspection in Phase 4.

## Validation provenance and configuration

The event/session/cwd/prompt requirements are the plan's explicit application contract, not newly verified CLI guarantees. All strings are preserved byte-for-byte after validation; required identifiers must have non-whitespace content. Optional metadata: absent allowed, null/empty/wrong type rejected when present. Prompt: empty and whitespace allowed; null/wrong type rejected. Unknown keys retained. Gateway validates JSON/event-name pair; common dispatcher validates session/cwd/optional metadata; event dispatcher validates prompt.

CLI hook: one occurrence required; string exact-match to payload. Shared options retain the old hook's operational ranges: finite deadline (0,300] seconds; positive context-character warning threshold; dependency depth integer0–20; dependency characters integer1–1000000. These are application policies inherited from current hook, not Claude payload fields. Argparse rejects malformed numeric types.

Repository root/config/real-opt-in: optional at generic transport layer; required/resolved only by the future feature adapter. No default root derived from cwd. Root existence/containment/provenance tests remain Phase4 dependency.
