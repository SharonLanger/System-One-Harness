# Phase 5 — caller and report migration

Shared gateway is wired to common ingestion, UserPromptSubmit ingestion, real root-mode flow and existing formatter. hooks/user_prompt_submit.py delegates once without parsing stdin or owning feature policy; it remains until final external plugin bindings can retire the old path. Replay/example callers use the module entry. Existing IDE entries call the migrated replay runner.

Astra-reviewed migration behavior: unrelated absolute cwd is retained metadata, while configured root remains source authority; the obsolete outside-cwd rejection test is replaced by explicit root-mode/containment tests. Phase0 fake accepted context now has valid collector shape; an independent literal expected protocol response remains. Invalid empty context still fails.

Replay records captured stdout as the exact payload oracle and keeps gateway preparation/final metadata separate. Historic full prepared records remain readable. Failed/incomplete output is described as potentially partial, never inferred NOT SENT from missing completion. Stale/unrelated PID/invocation records are excluded. Gateway records are metadata-only.

Astra-approved output recovery: broken pipe and timeout-interrupted protocol emission switch fd1 to devnull, preserving unknown partial count and avoiding repeated flush/delivery. Ordinary pre-emission failures do not redirect output. Logging failure after completed response preserves the established result.

Astra-approved logging adjustment: log_utils.log keeps best-effort behavior by default; gateway opts into raise_on_error=True to surface real filesystem failures to stderr without recursion or protocol contamination. Timeout always propagates. No logging framework or new debug switch.

Astra-approved lifecycle: absolute invocation budget includes argument-parsing time; timer stays armed through final logging. SIGALRM records expiration; no callbacks run afterward. Final/error logging timeouts do not retry logger or replace a completed response. Outermost finally cancels/restores timer handler. Invalid CLI before timer configuration has stderr evidence with invocation ID, no stdin read and no unbounded logger callback.

Checks before this phase commit: full Python789passed3existing skips; TypeScript122passed. Migration focused115passed; scenario suite50passed; root/replay contracts71passed; post-audit affected preparation/transport110passed. These counts overlap and are not additive. The final Phase6 run will execute the complete updated committed candidate and collect JUnit outcomes.

No real LAYA weights downloaded, Claude session started, plugin installed or global hook activated. Pinned official SDK structural contract verified; runtime/plugin/live checks remain separate conditional Phase7 work.
