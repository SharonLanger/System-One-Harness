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
