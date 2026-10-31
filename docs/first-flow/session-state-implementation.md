# First-flow session state: implementation handoff

## Behavior

The normal UserPromptSubmit adapter installs a final enrichment decision. Once complete source context passes the existing source checks and output budget, the flow checks session history and records one `context_enriched` event only when it commits to returning context. Duplicate selected file/name/signature/inclusive-range enrichment is suppressed until an exact later PostCompact state event. Checks, skips, errors and progress use regular debug logging exclusively.

The pure policy and event helpers live in `flows/first_method_context_utils.py`. The adapter uses `hooks/session_state.inspect_and_save_event`, which holds the existing per-session flock across CLI load, decision and conditional save. The existing TypeScript SessionStateStore still owns all JSONL parsing, timestamping and persistence. Legacy silent save requests remain supported; load responses are captured internally.

Missing/empty history permits enrichment. Ordinary read/write errors preserve prepared context with debug diagnostics. Corrupt history is never overwritten. Timeouts follow the gateway deadline. No retries, skip state records, synthetic compaction events, new dispatch registration or model calls were added.

## Test coverage map

- `tests/first_flow/test_session_policy.py`: empty history, repeats, intervening unrelated events, compaction intervals, exact boundary matching, distinct file/method/signature/ranges, legacy/malformed metadata, timestamp-order independence and summary validation.
- `tests/first_flow/test_session_flow.py`: finalizer metadata, allow/skip outcomes, early routes avoiding state, ordinary errors, exact session/deadline wiring, real sequential session fixture, invalid metadata, logger errors, timeout propagation and method-only fallback.
- `tests/test_session_transaction.py`: real bridge/store roundtrip, byte-preserving skip, PostCompact reenrichment, independent sessions, empty/corrupt history, callback/error lock release, invalid decisions/responses, expired deadlines, subprocess cleanup and no retries, concurrent processes and both controlled compaction lock orders.
- `tests/first_flow/test_hook_integration.py`: existing actual gateway protocol/source tests plus isolated temporary state; duplicate enrichment produces zero-byte stdout and unchanged session bytes.
- `typescript-helper/test/session-state-cli.test.cjs`: ordered load, missing-file read without creation, legacy silent saves, rejected unknown/ambiguous operations and existing bridge contract checks.
- Existing PostCompact and TypeScript store suites retain their regression coverage.

Public LAYA blocks are fixed/mocked; deterministic source utilities and selected integration storage paths run for real. Tests use temporary state roots. No experiments, real models, or tokenizers run.

## Validation

Results will be recorded after the final focused checks complete.

## Accepted limits

- State records commit to returning Context; they cannot acknowledge that Claude received it. Failure after append can suppress a later retry.
- Identity includes signature and line range. Moving/changing a declaration permits reenrichment. Body edits preserving identity remain suppressed; no content-freshness fingerprint is introduced.
- Direct calls to run without a finalizer remain stateless; hook adapters install it.
- The concurrency guarantee applies to cooperating Python bridge callers, including PostCompact. Direct TypeScript writers do not share the Python lock.
- Reads still validate/load full session history. This increment adds no index or compaction of the state file.

See [the authoritative design and test plan](session-state-design.md) for complete contracts and acceptance criteria.
