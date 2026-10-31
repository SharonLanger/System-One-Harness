# First-method-context: session-state enrichment and repeat suppression

Date: 2026-11-01
Status: reviewed design and implementation plan only. No implementation or tests executed.
Supersedes the earlier logging-only version of this document. Includes Sharon’s clarification: session state is persisted application state, not a diagnostic log. This document contains the design, implementation plan, and test handoff together.

## Outcome

At the very end of first_method_context, after valid context is completely prepared, decide whether to return it:

- No matching enrichment since the most recent PostCompact: return context and append one context_enriched event.
- Matching enrichment after the most recent PostCompact: return Noop and log why enrichment was skipped.
- Matching enrichment exists only before PostCompact: return context again and append a new event.
- Missing or empty session file: allow enrichment.

This is deterministic orchestration. Do not add a model question or change building blocks.

## Mandatory distinction: state versus debug logging

Session state is an append-only record of completed application actions used by later decisions. It is not a trace of execution. The filename ending in .jsonl does not make it a general-purpose debug log.

For first_method_context, the only state mutation permitted is one context_enriched append at the final enrichment commit point. Never append flow_started, context_prepared, enrichment_allowed, enrichment_skipped, validation results, errors, retry markers, or flow_finished to session state. The flow must not create a PostCompact entry itself. Existing PostCompact handling independently records the actual compaction action, unchanged.

The existing regular debug logger may record all useful progress, decisions, errors, and success details. Debug logging must not call the session-state writer. A missing state file must not be created merely to record a check or an early skip; creation of the existing separate lock file is not a state event.

| Situation | Session state mutation by this flow | Regular debug log | Hook result |
| --- | --- | --- | --- |
| Valid enrichment, new method | Append one context_enriched | Allow reason and confirmed save | Context |
| Valid enrichment after compaction | Append one context_enriched | Prior match and later compaction found | Context |
| Duplicate since last compaction | None | Skip reason and matching record | Noop |
| Early ineligible route or preparation failure | None | Existing reason/error | Existing Noop/Failure |
| History read fails | None; do not attempt an unchecked append | Read failure; enrichment continues without state guarantee | Prepared Context |
| State save fails | No second write or error event; append may be uncertain | Save failure, never false save success | Prepared Context for ordinary error |
| Existing PostCompact hook executes | That hook appends its existing PostCompact event | Existing hook diagnostics | Existing hook result |

“Performs enrichment” means the flow has completed preparation, passed the final decision, and committed to returning that exact Context. Merely preparing text does not qualify. Delivery to Claude is not acknowledged by this API; the delivery limitation below still applies.

## Review of the earlier design

Keep the existing event envelope, session-specific destination, store-generated timestamp, project-root source resolution, and clean hook output. Correct these gaps:

1. Add selected method line ranges.
2. Replace the write-only success callback with a final decision seam that can return allow or skip.
3. Read existing history through the existing store, which already exposes load().
4. Perform history check and conditional append under one existing per-session lock. Separate unlocked read and write permits duplicate concurrent enrichment.
5. Use append order, not timestamp sorting, to establish whether compaction happened afterward.
6. Remove the previous requirement to append on every repeated successful preparation. A suppressed attempt is not enrichment.
7. Keep flow-specific policy in a flow utility, not inside a LAYA building block or the generic storage class.

## State event contract

Use the existing envelope. Do not rename type to mean source kind; the two fields answer different questions.

```json
{
  "timestamp": "2026-11-01T08:30:00.000Z",
  "source": {
    "kind": "flow",
    "name": "first_method_context"
  },
  "type": "context_enriched",
  "payload": {
    "files": [{
      "filePath": "/projects/shop/src/billing/invoice-service.ts",
      "methodNames": ["calculateInvoiceTotalWithAdjustment"],
      "methods": [{
        "name": "calculateInvoiceTotalWithAdjustment",
        "signature": "calculateInvoiceTotalWithAdjustment(amount: number): number",
        "startLine": 42,
        "endLine": 68
      }]
    }]
  }
}
```

The signature and lines above are illustrative; copy real metadata from the selected callable/extraction result. Lines are 1-based, inclusive, and describe the selected implementation actually included in additionalContext, including the declaration as represented by the extractor. Do not infer them by counting rendered context lines.

- source.kind = flow; source.name = first_method_context.
- type = context_enriched, the action.
- timestamp comes from SessionStateStore.
- filePath is the canonical absolute source path, resolved using the explicit analyzed project root.
- methodNames retains the existing documented convention. methods adds the corresponding structured detail. For this flow both arrays contain exactly one consistent selected method.
- No prompt, source implementation, called-method list, token counts, or full additionalContext in state.
- Do not repeat session ID in every event; the destination identifies the session.

The optional methods payload extension fits the store's existing JSON payload contract. No generic event-envelope schema migration is needed. Keep methodNames and methods consistent in one event-construction helper rather than populating them independently.

Existing compaction events stay unchanged:

```json
{
  "timestamp": "2026-11-01T08:35:00.000Z",
  "source": {"kind": "hook", "name": "PostCompact"},
  "type": "PostCompact",
  "payload": {}
}
```

Only this exact hook source/name/type combination is a compaction boundary. An arbitrary flow event mentioning compaction is not.

## Destination and append semantics

Reuse:
```text
<existing LCR runtime logs root>/session-state/<sessionId>.jsonl
```

Append to the end of the file belonging to the current session ID. “Last JSONL file” means the end of this session's file, never whichever file has the newest modification time. Do not truncate, rotate, rewrite history, or create a new file per prompt. Missing files are created by the existing writer when an enrichment is recorded.

The runtime logs root remains anchored to the installed LCR runtime, shared with PostCompact. It is distinct from the analyzed project's root. Neither source lookup nor destination selection should fall back to process cwd.

## Matching a previously enriched method

Only inspect context_enriched records with source.kind=flow and source.name=first_method_context.

For new structured records, match canonical filePath plus method name, signature, startLine and endLine. This conservative identity avoids treating two same-named methods in one file as the same callable. Reuse existing signature and source-range metadata; do not invent a parser or persist snapshot-specific opaque callable IDs.

Consequences, explicitly accepted for this version:

- A declaration moving lines or changing signature can be enriched again without compaction.
- A body edit that preserves name/signature/range is still considered the same method and is suppressed. This implements session deduplication, not code freshness. Source-content fingerprinting is a separate future policy.
- Relative paths are not resolved against today's cwd when reading old records. Only canonical absolute identities match.
- Legacy events with filePath and methodNames but no structured methods are insufficient to disambiguate callables. Ignore them for suppression, log legacy_metadata_ignored if relevant, and allow one new structured enrichment.
- Valid unrelated events are ignored. Malformed candidate metadata must not cause a match.

Do not let called-method navigation rows suppress enrichment of those callees later: only the selected implementation counts.

## Final decision algorithm

Expose a small flow method, finalize_enrichment, invoked once at the success tail. Put its pure history policy and event-summary construction in a flow-local utility such as src/laya_context_router/flows/first_method_context_utils.py. This is a utility for the flow, not a new building block.

A pure helper, decide_enrichment(history, selected), returns an explicit decision with allow, reason, and optional matched event / compaction positions for diagnostics.

Algorithm over validated events in their JSONL order:

1. Locate the last exact PostCompact event, or use index -1.
2. Search after that boundary for any matching selected-method enrichment.
3. If found, return skip/already_enriched_since_compaction.
4. Otherwise allow. If a matching enrichment exists before the boundary, reason is compaction_after_enrichment. Otherwise reason is not_previously_enriched.
5. Missing/empty history yields allow/no_history.

Searching only for the latest prompt is incorrect: an unrelated intervening prompt does not remove earlier context. Search matching enrichment records within the current compaction interval.

Examples:

| History, oldest to newest | Current candidate | Decision |
| --- | --- | --- |
| Empty | A.m1 | Enrich |
| Enrich A.m1 | A.m1 | Skip |
| Enrich A.m1, enrich B.m2 | A.m1 | Skip |
| Enrich A.m1, PostCompact | A.m1 | Enrich again |
| Enrich A.m1, PostCompact, enrich A.m1 | A.m1 | Skip |
| PostCompact, enrich A.m1 | A.m1 | Skip |
| Enrich A.m1, PostCompact, PostCompact | A.m1 | Enrich again |
| Enrich A.m1 | A.m2 | Enrich |
| Enrich A.m1 in another session | A.m1 | Enrich |

Compaction allows re-enrichment; it does not prove that the method was actually removed from Claude's context. That is the requested conservative policy.

## Flow integration and side-effect ordering

Preserve existing classification, method_selection_v2, source utilities, navigation, source snapshot checks, UTF-16 output budget, and exact code formatting.

Success path:

1. Finish all extraction, navigation, source validation and context packing.
2. Construct the Context and selected-method metadata in memory.
3. Invoke the final decision seam supplied by handle_prompt.
4. Under the session transaction, load history and run the pure decision helper.
5. If skipped, append no enrichment event and return Noop with reason already_enriched_since_compaction.
6. If allowed, append the context_enriched event while retaining that lock, then return the prepared Context.
7. Emit best-effort diagnostics reflecting the actual outcome. Do not run fallible flow transformations after committing the event.

Move existing success-only diagnostics so suppressed runs are not reported as successfully enriched. A preparation diagnostic may say context_prepared, but must not claim context was returned. Preserve existing optional debug logging of exact enriched text; do not reformat source code.

Replace the old proposed on_enrichment notification callback with an optional finalize_enrichment callback returning an explicit allow/skip result. handle_prompt binds the current session ID, logger and exact gateway deadline. Direct run callers without that seam retain stateless behavior; normal hook dispatch must always supply it. Tests must prove this wiring.

Only a valid final Context reaches this seam. Paths with no file, unsupported action, no selection, failure, overflow or source-snapshot mismatch must neither consult history nor append an enrichment record. Valid method-only context after ordinary navigation failure does reach it.

## Reuse storage; add only the missing bridge capability

Verified current code:
- TypeScript SessionStateStore already has save() and load().
- Python hooks/session_state.py exposes only save_event and owns the cooperating-process session flock.
- session-state-cli.ts currently supports only saving an event and emits no stdout on success.
- PostCompact uses save_event with the same session lock.

Plan:

1. Extend the existing CLI with an explicit load operation, returning one JSON response containing events in stored order. Preserve today's save request shape and zero-output save behavior for backward compatibility.
2. In hooks/session_state.py, extract only the shared lock/deadline/subprocess plumbing needed by the existing save path and a new transaction helper.
3. Provide a narrow helper such as inspect_and_save_event(session_id, decide, *, deadline, ...). It acquires the same session lock, loads through the CLI, invokes the supplied pure decision callback, optionally saves through the CLI while retaining the lock, and returns the decision.
4. Use internal already-locked bridge calls. Do not call the public save_event from inside the locked transaction and risk acquiring the same lock twice.
5. Keep the generic bridge unaware of method matching or PostCompact policy. The flow utility supplies that decision.
6. Capture and validate load-response stdout internally. Never forward subprocess stdout to hook stdout. Existing gateway serialization alone writes the hook response.

Holding one Python lock across two bounded CLI calls is sufficient for cooperating hook processes; the TypeScript store owns parsing and persistence throughout. No new store, alternate Python JSONL parser, separate CLI or standalone index is needed.

All operations share request.config.deadline_at. Lock waits and both subprocess calls consume the same remaining budget; do not restart the timeout. Release locks and terminate subprocesses on failure exactly as the current adapter does.

The same session lock serializes PostCompact with enrichment transactions. Two simultaneous identical candidates therefore produce one stored enrichment and one skip when storage succeeds. Direct writers bypassing the Python lock are outside this guarantee.

## Failure policy and meaning of success

Ordinary state-read or state-write failure is fail-open: return the otherwise valid Context with a diagnostic indicating deduplication/state persistence was unavailable. Never suppress based on unreadable history. Never overwrite, repair or truncate corrupt history automatically.

Missing/empty history is a normal allow result. Corrupt JSONL, permissions, invalid session ID, missing Node/helper, malformed bridge responses and unavailable session metadata are errors, not empty history; report their distinct categories.

TimeoutError propagates to the existing gateway deadline handling. Do not retry an uncertain append automatically. Only claim session_state_saved after confirmed success.

State events record a committed decision to return prepared enrichment. They cannot guarantee Claude received it: the process can fail between append and hook delivery. This existing limitation becomes meaningful with suppression: such a record could suppress a later retry. Exactly-once delivery would require a gateway acknowledgment protocol outside this task. Do not silently claim that guarantee.

Diagnostic logger errors must not convert a committed decision into a normal flow failure. Preserve deadline handling, but otherwise keep diagnostics best-effort.

## Diagnostics

Use the existing structured logger, never print:

| Diagnostic | When | Useful fields |
| --- | --- | --- |
| enrichment_skipped | Matching event in current interval | flow, session_id, file, method, start/end lines, reason, matching event index |
| enrichment_allowed | New candidate or compaction invalidated prior match | same identity, reason, optional prior enrichment and compaction indices |
| session_state_saved | Append confirmed | flow, session_id, event_type |
| session_state_enrichment_failed | Read/decision bridge/write unavailable | operation, error category, flow, session_id |
| legacy_metadata_ignored | Relevant old record lacks unambiguous identity | flow, record index |

Do not append skip events into session state in this increment. They belong in operational logs and must never be interpreted as proof that context was enriched.

## Detailed tests

Mock public LAYA building blocks and default persistence seams; keep deterministic utilities real. Reuse tests/first_flow fixtures and existing block mocks. Copy any needed experiment fixture into tests; never modify experiments. No live model or tokenizer.

### Pure history policy

| Test | Expected |
| --- | --- |
| No records / missing file represented as [] | Allow/no_history |
| Matching structured enrichment | Skip |
| Match then unrelated event | Skip |
| Match then exact PostCompact | Allow/compaction_after_enrichment |
| Match, PostCompact, new match | Skip |
| Multiple compactions, no later match | Allow |
| Compaction before matching enrichment | Skip |
| Same method name, different canonical file | Allow |
| Same file/name, different signature or range | Allow |
| Same candidate body changed but identity unchanged | Skip, documenting this version's policy |
| Other flow's context_enriched event | Ignore |
| Flow event named PostCompact or wrong hook type | Not a boundary |
| Equal or decreasing timestamps | Decisions follow append order |
| Legacy names-only enrichment | Allow; no ambiguous suppression |
| Malformed candidate metadata within valid generic event | Ignore safely |
| Callee listed only in navigation | Does not count as enriched |

### Flow and adapter behavior

| Test | Expected |
| --- | --- |
| Explain / generate_tests successful context | Finalize once with selected canonical path, signature and inclusive lines |
| Decision allows | Exact prepared Context returned, correct event metadata |
| Decision skips | Noop; zero hook-output bytes; skip diagnostic; no context_enriched append |
| All early skips/failures/overflow/source mismatch | Finalizer not called |
| Valid method-only fallback | Finalizer called normally |
| Real hook adapter | Session ID and exact deadline passed; finalizer always installed |
| Direct run without callback | Existing stateless contract preserved |
| Different cwd, decoy project and logs paths | Correct explicit project/root identities and runtime log destination |
| Ordinary load/write failure | Context retained, error diagnostic, no false saved claim |
| Deadline expires during load, lock wait or save | Existing timeout path, lock released, no retry |
| Diagnostic logger ordinary error | Does not change allow/skip decision or corrupt output |
| Metadata / code fidelity | Exact source lines and text preserved; no metadata added to hook wire schema |

### Existing bridge/store integration, temporary directories only

- First call creates session file; second identical candidate skips; byte content unchanged by skip.
- Append PostCompact through existing save_event; next identical candidate appends enrichment; following call skips.
- Two session IDs remain independent.
- Earlier JSONL bytes remain intact; every appended record parses and has a store timestamp.
- Missing and zero-byte file behave as no history; corrupt file is not treated as empty or overwritten.
- Load operation captures internal JSON; existing save operation remains silent.
- Two cooperating processes race on the same candidate: one append, one skip, valid JSONL.
- Serialize PostCompact and enrichment in both controlled lock orders; resulting decisions follow that order.
- Lock release after callback/subprocess error allows a later operation to proceed.
- Preserve existing PostCompact save tests and deadline behavior.

Use synchronization primitives rather than sleeps for concurrency tests. Build the existing helper as an integration-test prerequisite. Avoid duplicating exhaustive store validation tests already present.

## Instructions and scope for Sol

1. Read repository AGENTS.md and current source before implementing.
2. Add the flow-local utility and final decision seam.
3. Extend only existing bridge plumbing/CLI as needed for load plus conditional save under one lock; leave the store format and core save/load behavior intact.
4. Wire handle_prompt and add the tests above in existing suites.
5. Run relevant flow, bridge/store, PostCompact and hook-contract tests; report actual results.
6. Update repository design documentation and submit changes for review; do not merge automatically.

No changes to sandbox, experiments, block questions/rules, tokenizer, navigation/parser behavior, hook dispatch registration, plugin flags, or output format. In particular, do not add --log-state to UserPromptSubmit.

If an unexpected deviation is necessary, send Astra a focused description of the mismatch and smallest options before making that deviation. Routine implementation choices within this plan do not need repeated review.

## Implementation handoff: contracts and sequence

The paths below are relative to the repository root. Proposed function names are design names, not claims that these APIs already exist. Reuse current naming and typing conventions where possible without changing behavior.

### Responsibility map

| Location | Responsibility | Must not do |
| --- | --- | --- |
| src/laya_context_router/flows/first_method_context_utils.py | Selected-method summary, pure history decision, enrichment event construction | File I/O, subprocesses, LAYA calls, debug/state writes |
| src/laya_context_router/flows/first_method_context.py | Finalize prepared context; handle_prompt binds session services | Parse JSONL, implement locking, change block behavior |
| src/laya_context_router/hooks/session_state.py | Deadline-bound locked read/conditional append bridge | Understand file/method/compaction business rules |
| typescript-helper/src/session-state-cli.ts | Dispatch existing save or new load operation | Emit diagnostic data in successful protocol responses |
| typescript-helper/src/session-state.ts | Existing parsing, validation, append, timestamp, load | New flow-specific policy |
| Existing regular logger | Diagnostic observations | Become another session-state writer |

The hook dispatcher already routes this flow. No new dispatcher registration should be required.

### Data contracts

Use the repository's existing dataclass/TypedDict conventions; avoid introducing a schema framework.

SelectedMethod:
- file_path: canonical absolute path, from resolved selected source.
- name: actual selected method name.
- signature: existing extractor/outline signature for that callable.
- start_line and end_line: positive integers, inclusive, end_line >= start_line. Reject booleans as integer values.
- No session ID, prompt or implementation text is needed in this summary.

EnrichmentDecision:
- allow: boolean.
- reason: no_history, not_previously_enriched, compaction_after_enrichment, or already_enriched_since_compaction.
- matched_event_index: optional zero-based JSONL event position.
- latest_compaction_index: optional zero-based position.
- Additional diagnostic metadata, if needed, stays internal.

Keep state availability separate from policy: storage read failure is not a successful no_history decision. The adapter handles that error and returns valid prepared context with a failure diagnostic.

Pure utility contracts:
- decide_enrichment(history, selected) -> EnrichmentDecision; deterministic, no side effects, does not mutate history.
- build_enrichment_event(selected) -> SessionEventInput; no timestamp supplied, exactly one selected file and method, methodNames agrees with methods.
- Validate selected metadata before requesting a state transaction. An unexpected missing/invalid summary preserves prepared context with a debug error and performs no state write. Escalate an extractor contract mismatch to Astra during implementation instead of inventing line values.

Transaction helper contract:
- inspect_and_save_event(session_id, decide, *, deadline, existing test/config overrides).
- Under the session lock, load events and call decide(history) exactly once.
- The callback returns the decision plus an optional event: skip pairs with no event; allow pairs with one enrichment event.
- On skip, return decision without invoking save.
- On allow, save the event using the already-held lock, then return decision.
- Invalid callback result raises an integration error before save; never silently append a fabricated event.
- Callback exceptions, load errors and save errors release the lock and propagate to the flow adapter. They are not written into state.
- The adapter distinguishes confirmed save from ordinary fail-open behavior for debug messages.

Do not pass the Context or its source code through the session-state bridge. It stays in the flow while only the small summary/event travels to persistence.

### CLI protocol additions

Keep existing request {logsRoot, sessionId, event} working unchanged as save. Add an explicit operation field for load:

```json
{"operation":"load","logsRoot":"/runtime/logs","sessionId":"session-123"}
```

Successful load response on captured subprocess stdout:

```json
{"events":[]}
```

Return events in stored append order, with their existing timestamps. Empty/missing state returns an empty array through SessionStateStore.load(). Explicit save may be supported if useful, but the legacy save request must remain supported. Reject unknown operations and load requests carrying an event rather than guessing their intent.

Keep the existing input-size bound. Successful save emits zero bytes. Failed load/save emits the existing error format on stderr and a nonzero exit status. The Python adapter validates the load response envelope and array before invoking policy; a nonzero exit or malformed response must not be interpreted as empty history. Do not add prompt/source data to requests.

### Incremental implementation plan

Complete each testable increment before building on it. Commit boundaries may follow these steps; do not create unrelated cleanup commits.

1. **Pure policy and metadata**
   - Read current flow metadata contracts and reuse existing fixtures.
   - Add summary/event helpers and history decision.
   - Run pure tests, including repeated enrichment and compaction ordering.
   - Exit: policy is deterministic and event payload includes correct ranges.

2. **Read bridge**
   - Extend the existing CLI with load, keeping save compatible.
   - Add focused protocol tests and a temporary-store read round trip.
   - Exit: missing history reads as []; save remains silent; errors remain errors.

3. **Locked conditional state mutation**
   - Extract shared lock/subprocess plumbing narrowly.
   - Add inspect_and_save_event without nested acquisition.
   - Test callback-once, skip-without-save, lock release, deadlines, and two-process behavior.
   - Exit: check-and-append is serialized with existing PostCompact saves.

4. **Final flow integration**
   - Install the finalizer through handle_prompt.
   - Call it only after all existing context eligibility checks.
   - Map skip to Noop and allow to the exact prepared Context.
   - Add ordinary debug diagnostics and preserve the existing source-formatting log.
   - Exit: mocked-block flow tests prove all routing and no unwanted state mutations.

5. **Hook and session acceptance**
   - Run the sequential session scenario and gateway stdout tests.
   - Run relevant existing PostCompact, store/bridge, and first-flow regression suites.
   - Inspect the diff for out-of-scope changes.
   - Exit: documented results, reviewable PR, no automatic merge.

For each increment, record exact test commands and results in the implementation handoff/PR. Discover build and test commands from the current repository configuration; do not guess obsolete commands or report unrun tests as passed. Broaden testing only when shared changes or observed failures justify it.

## Additional mandatory test cases: state is not debug

These cases supplement the policy and integration matrices above. Each test must assert the observable outcome, not only a mock call count.

| ID | Setup and action | Required assertions |
| --- | --- | --- |
| STATE-01 | Eligible first enrichment; capture debug and state separately | One context_enriched record; correct kind/name/file/method/lines; no diagnostic records in state |
| STATE-02 | Same eligible method repeated in same session | Noop, zero stdout bytes, unchanged state bytes, enrichment_skipped in regular debug |
| STATE-03 | Emit several debug progress and success messages during one enrichment | State still receives exactly one enrichment event |
| STATE-04 | Early no-file/unsupported/no-selection route with no state file | State file remains absent; finalizer and writer not called |
| STATE-05 | Preparation error/overflow/source mismatch with existing history | Exact prior state bytes preserved; no error/state marker appended |
| STATE-06 | Successfully prepare text, then final history decision says skip | No successful-enrichment diagnostic; prepared context not returned; no state append |
| STATE-07 | New method in existing session | Append one selected-method event; prior bytes remain unchanged |
| STATE-08 | Real PostCompact between two same-method enrichments | State types are exactly context_enriched, PostCompact, context_enriched; subsequent repeat leaves three records |
| STATE-09 | Flow reads a compaction record | No synthetic compaction event written by the flow |
| STATE-10 | Writer raises before append | Valid Context, regular debug error, no saved claim and no retry/error event |
| STATE-11 | Writer outcome uncertain after interruption | No automatic retry or compensating marker; timeout follows gateway contract |
| STATE-12 | Reader raises on malformed history | No save attempt, unchanged corrupt bytes, ordinary-error fail-open Context and debug error |
| STATE-13 | Regular debug logger raises ordinary exception | State/decision contract unaffected; no fallback debug write into state |
| STATE-14 | Captured load response contains internal state JSON | That JSON never appears in gateway stdout; only existing Context serialization or zero bytes |
| STATE-15 | Selected metadata invalid | No state access/write; debug integration error; otherwise prepared Context retained |
| STATE-16 | Two methods share a name in different classes/ranges | One method's record does not suppress the other |
| STATE-17 | File path contains spaces/Unicode | Exact canonical path preserved in state; no shell interpolation or path corruption |
| STATE-18 | Two eligible sessions use same method | One independent record per session; one session's compaction does not affect the other |

### Sequential acceptance fixture

Create this fixture under tests using the existing example TypeScript project or a copied subset. Mock requested_action and method_selection_v2; leave source utilities real. Use a temporary logs root and the real existing bridge/store for this one scenario.

1. Session S1 requests method A: Context returned; one enrichment event.
2. S1 requests A again: Noop; still one event; skip debug record.
3. S1 requests method B: Context; two enrichment events.
4. S1 requests A again: Noop; still two events.
5. Save a real-shaped PostCompact through the existing adapter: three events.
6. S1 requests A: Context; four events, last is A enrichment.
7. S1 requests A again: Noop; still four events.
8. Session S2 requests A: Context; one event in S2, S1 unchanged.

At every stage assert identity/ranges, state record count and order, debug category, and hook output contract. Compare output code with the fixture's extracted source, not a manually reformatted copy.

### Concurrency and cleanup details

Use two independent processes for the same-session transaction test so Python flock is genuinely exercised. Coordinate their entry with barriers/events or pipes, and use bounded test timeouts. Assert one allow, one skip and one enrichment event; always terminate/join workers in fixture cleanup. Do not rely on a fixed sleep to make a race occur.

For PostCompact ordering, force two scenarios separately: compaction commits before the final history read, and compaction waits until after enrichment commits. Assert state append order and the next prompt's decision, not wall-clock timestamp order.

All integration tests own temporary state and lock directories. No test may use real user/session runtime state. Keep build prerequisites explicit. Unit tests remain runnable with fake bridge responses and public block mocks, without a model.

## Final review checklist for the implementing agent

- [ ] Only performed enrichment produces state mutation from this flow.
- [ ] Existing PostCompact is preserved as an independent state action.
- [ ] All checks, skips, progress and errors use the regular debug logger only.
- [ ] File/method/range metadata comes from the selected implementation.
- [ ] Pure policy and generic persistence responsibilities remain separate.
- [ ] Check plus append shares the existing per-session lock and deadline.
- [ ] No early route consults state; no skip changes JSONL bytes.
- [ ] No stdout leakage, source reformatting, output-budget changes, or model/block changes.
- [ ] Missing/empty history, corruption, ordinary failures and timeouts are tested distinctly.
- [ ] Existing save CLI and PostCompact tests still pass.
- [ ] Experiments and sandbox remain untouched.
- [ ] Report changed files, test results, known delivery/freshness limitations and deviations.
- [ ] Ask Astra for a focused decision on necessary plan deviations; document the resolution.
- [ ] Submit the PR for Sharon's review; do not merge.

This document is ready for implementation planning by the next agent. Writing this handoff does not execute the implementation, build, or tests.

## Acceptance

A session receives a structured enrichment record with source kind/name, action, file, selected method and lines. The same candidate is suppressed until a later recorded PostCompact, after which it can be enriched and recorded again. Empty history allows enrichment. Final decisions are made only at the end of the flow, use the existing session store and lock, and leave hook stdout clean.

Reviewed against current main on 2026-11-01:
- typescript-helper/src/session-state.ts
- typescript-helper/src/session-state-cli.ts
- src/laya_context_router/hooks/session_state.py
- src/laya_context_router/hooks/post_compact/dispatcher.py

No implementation changes were made as part of this review.
