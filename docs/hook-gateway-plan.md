# LCR Hook Gateway — three-layer entry design and test plan

Status: core Phases 0–6 implemented and verified on PR2; Phase 7 plugin/live work deferred. Phase evidence is authoritative for executed checks. Original design and critical review follow, with D07/D02 amendments below.
Prepared for Sharon, 30 October 2026. Revision 2: critical review, top-down implementation phases, unit scenarios, and concurrent PR workflow.

This revision is ready for Sol to implement when Sharon starts that work. Planning here does not create a branch, PR, application commit, or merge.

## 1. Scope and relationship to previous plans

This is a focused addendum to `docs/implementation-plan.md`, grounded in `hooks/user_prompt_submit.py` and `tests/test_prompt_hook.py` at inspected main commit `91ec04b1b3f74cf6c41da530d7b00c7ca34d8ef5`. It replaces the earlier proposed placeholder UserPromptSubmit behavior: this version routes to the existing real prompt-context flow, retaining its explicit model opt-in and configuration. It does not authorize implementing Stop recovery, YAML rule execution, state storage, or other features from `lcr-recovery-design-handoff.md`.

The previous recovery handoff proposed `{}` for no-action responses. For this entry-point work, retain the observed existing contract: EMPTY stdout and exit 0 on normal no-op. A report's `response: null` means no response object exists; never serialize that null onto stdout.

Sharon will supply the plugin folder, plugin manifest JSON, and hooks JSON. Their actual names, paths, script command, and registration mechanism remain pending. Add README installation instructions only after asking Sharon for his preferred setup. Do not invent those files or activate hooks now.

## 2. Names: components and methods

Use **Hook Gateway** as the shared process boundary. It receives every registered command-hook invocation through ONE public executable entry, proposed as `python -m laya_context_router.hooks.gateway --hook UserPromptSubmit`. The hook name is the only event-specific command argument. Existing operational configuration (project root, model settings, deadlines, budgets, explicit real-mode opt-in) remains available through one shared configuration mechanism; do not remove it while adding the hook-name argument. Final launch syntax awaits Sharon's hooks JSON.

Names of components are not executable functions:

- Hook Gateway: shared process boundary; public method `main(argv=None)` in `laya_context_router.hooks.gateway`.
- Main dispatcher: internal method `dispatch_hook(envelope, services)`.
- UserPromptSubmit dispatcher: event-specific method `dispatch_user_prompt_submit(envelope, services)`.
- Prompt Context Enrichment: feature name; internal method `enrich_prompt_context(request, services)`.
- `UserPromptSubmit`: exact Claude event string, not a method.
- `prompt_context_enrichment`: internal feature identifier used in logs, not a Claude event.

This preserves one public entry point, with ordinary internal methods below it. No hook-specific script reads stdin or prints protocol output.

## 3. Proposed code placement

The plugin folder contains registration assets supplied by Sharon. The application gateway belongs in the package, separate from registration assets. Keep the gateway, contracts, and event-specific dispatchers together inside the package `hooks` folder, rather than using a top-level folder as the application entry.

Proposed paths (not created by this plan):

```text
src/laya_context_router/hooks/gateway.py
src/laya_context_router/hooks/contracts.py
src/laya_context_router/hooks/user_prompt_submit/dispatcher.py
src/laya_context_router/hooks/user_prompt_submit/prompt_context_enrichment.py
src/laya_context_router/flows/file_method_context.py  # existing flow reused
```

The old `hooks/user_prompt_submit.py` combines transport, validation, model setup, flow invocation, formatting, and emission. Extract those responsibilities into these layers. Decide its removal or a temporary forwarding wrapper only after examining Sharon's supplied registrations and the experiment/run-configuration callers. A temporary wrapper must delegate to the gateway; it must not retain a second implementation.

## 4. Invocation and data ownership

1. Claude starts the shared command with `--hook <event-name>` and supplies event JSON on stdin.
2. The gateway reads stdin exactly once, within the total invocation deadline and input limit. Parse strict JSON with duplicate-key rejection, retaining the original object.
3. Validate the argument and payload `hook_event_name`. Both must exist and match exactly. Never silently prefer one when they conflict.
4. An invocation ID is created before parsing so malformed input is traceable. After checking the event-name pair, main dispatch looks up the supported event contract. Unknown events return unsupported_event immediately; known events validate the common fields required by that contract and build the envelope. Root/model configuration is resolved only when the selected feature needs it.
5. Call a named enrichment seam, initially identity-only, then look up the event dispatcher through an explicit registry. No arbitrary import from user-supplied hook names.
6. UserPromptSubmit dispatch validates its specific fields and logs the ingested input. It creates a typed request for Prompt Context Enrichment.
7. The feature reuses `flows.file_method_context.run`, the current model client, selection rules, source helper, and context formatter. It returns an internal result to its dispatcher, then to the gateway.
8. Only the gateway converts the result into Claude JSON, writes at most one response, and records final outcome metadata. A normal no-op writes zero bytes to stdout.

Input parsing means JSON decoding at the gateway once, then schema validation/adaptation at each layer. Do not decode the JSON again or discard fields when passing between layers.

## 5. Layer 1: common envelope and enrichment seam

Proposed envelope fields:

- `hook_name`: validated command argument matched to payload event.
- `invocation_id`: generated once per process invocation, separate from session ID.
- `common`: validated common input metadata.
- `raw_payload`: unmodified full input object, including additional fields.
- `derived`: application-derived information, initially empty.

For the first supported UserPromptSubmit adapter, the application requires nonempty `session_id`, absolute string `cwd`, and exact `hook_event_name`; the event dispatcher requires string `prompt`. The pinned official Anthropic SDK contract resolves the provisional fields: transcript_path is required nonempty string; permission_mode is optional and validated as nonempty string when supplied. Never read the transcript or enforce a fixed permission-mode enum. Check nonempty identifiers without silently trimming or rewriting them. The final Phase 0 field ledger must state required/optional, type, empty/null policy, source, and validating layer for every consumed field. Tests follow that ledger. Different events can have different common-field requirements; no universal event-schema assumption.

Retain additional payload fields unchanged for forward compatibility. Missing required fields, nulls, and wrong types are validation failures, never valid no-ops. Optional fields remain optional; do not invent values or reject an event just because it lacks an unused optional property. For valid empty user prompt text, pass the empty string through and let the feature return a normal no-op if appropriate.

Reserve `enrich_envelope(envelope, services)` as an identity function now: return the same validated values with an empty derived object. Later it can attach project metadata or filters without changing dispatcher signatures. Filters themselves are deferred.

`derived.project_root` is a future enrichment field with source/provenance metadata. Project root is not assumed to be in Claude's standard payload. Never overwrite raw `cwd` or silently substitute cwd as root.

The existing feature already requires a repository root. During this migration, the typed feature request obtains `project_root` from the existing explicit application configuration, validated once and labeled `source: explicit_configuration`. This is configuration resolution, not the new enrichment implementation. Missing root fails before source reads/model calls. When root enrichment is later implemented, define precedence and conflict detection explicitly; no automatic git discovery, environment fallback, or session persistence is included now.

The target is project-root-based reference resolution and displayed paths, following Sharon's updated requirement. The merged root/formatter/navigation change is already present at984aa. Astra D07 approves an explicit resolve_from_project_root=False extension to the existing flow/resolver facade, preserving legacy defaults. Gateway opts in with True; the facade documents translating configured root into the generic helper lookup-base argument while raw event cwd stays unchanged. Reuse the existing search algorithm and source containment. No new resolver or navigation operation is introduced. All selected source access remains confined to the configured project root. See Phase 4 and the conflict workflow.

## 6. Layer 2: UserPromptSubmit dispatcher

Input: common envelope, explicit application configuration, services. It knows the UserPromptSubmit schema and requires `raw_payload.prompt` to be a string. It retains raw metadata and adds a validated prompt field to its request. Do not normalize whitespace, reinterpret user text, or forward the entire raw object to LAYA.

Log `hook_input_ingested` after successful validation, with event, invocation ID, session ID, field names, prompt length, cwd, and configured root provenance. New gateway/dispatcher logs use metadata by default. Reuse an existing debug setting if available; do not introduce a project-wide logging redesign. Existing lower-level logs may already contain full prompts, so this proposal does not promise global redaction. Each layer records what it ingested without duplicating model calls.

Call exactly one handler in v1: `enrich_prompt_context`. Return its result without printing. Keep this call isolated so a future ordered handler registry can be added here. Do not implement multi-handler execution, priorities, merging, or response composition now.

## 7. Layer 3: Prompt Context Enrichment handler

Input: typed UserPromptSubmit request containing prompt, session/invocation metadata, validated project root, retained cwd, and current model/budget configuration.

Behavior: invoke the existing file/method context flow once and format an accepted context once. Preserve the current method-selection questions, thresholds, model semantics, ambiguity behavior, dependency collection, and model opt-in. The new dispatcher structure does not itself justify changing LAYA's decisions or confidence handling.

Output uses an explicit internal result union:

```text
Context(text, feature_id)
Noop(reason, feature_id)
Failure(code, stage, field?, message)
```

`multiple_relevant` is a normal `Noop`, not a validation error. Missing prompt/session ID/root is a `Failure`, not `Noop`. Unexpected result shapes and an empty Context text are failures. The internal Context result contains text, not pre-serialized Claude JSON. This avoids each future feature independently printing incompatible responses.

## 8. Return contract and error behavior

On Context, gateway emits exactly one JSON object and newline using the standard serializer:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "Actual formatted context text"
  }
}
```

On normal Noop, stdout is empty and process exit is 0. No `{}`, JSON `null`, or diagnostic text is sent.

Validators raise a typed validation exception; dispatcher/feature boundaries return the explicit Failure result. The gateway catches uncaught exceptions once. Validation/processing failures are ERROR-level logged with stage and field, and are asserted as failures in unit tests. At the outer command boundary, retain the current nonblocking policy: empty stdout and exit 0 for handled errors, with a clear stderr diagnostic and `outcome: error` in logs. This must not be recorded as a successful no-op. Exit 0 indicates the hook did not block Claude, not that enrichment succeeded. Do not introduce exit 2 or prompt blocking under this refactor. If Sharon later wants malformed input to block Claude, that requires an explicit separate policy decision.

Unregistered event: explicit `Noop(unsupported_event)`, no feature/model import or execution. A known event with an invalid schema is a Failure. Register only event types supported by the supplied JSON and adapters; special hook outputs such as worktree creation require their own contract before activation.

## 9. Observable logs and proof of output

Reuse the current logger. Every record carries invocation ID, event and session ID when validated. Before session validation, use invocation ID and field-error metadata.

Proposed ordered records:

1. `gateway_received`: argument/payload event, payload field names, input size.
2. `common_input_validated`: extracted common fields and derived field names.
3. `hook_input_ingested`: UserPromptSubmit validation completed.
4. `feature_started`: `prompt_context_enrichment` and relevant configuration metadata.
5. `feature_finished`: context/noop/error, reason, duration.
6. `response_prepared`: context only, response event and serialized byte count.
7. `gateway_finished`: outcome, reason/error code, `response_present`, `stdout_bytes_written`, exit code.

A no-op final record must explicitly include `response_present: false`, `stdout_bytes_written: 0`, and its reason. A failure has `outcome: error` and its error code. A context result is marked emitted only after a successful write/flush. Broken pipe/write failure must not produce a false successful emission record.

Logs show application intent and observed writes. A subprocess capture of exact stdout independently verifies bytes at the process boundary. Neither is an acknowledgement that Claude parsed or used a response. Keep replay reports showing captured stdout, parsed response, process exit, outcome, and error separately, as the current experiments do. Logger failure is surfaced to stderr and must not contaminate stdout or erase the semantic result. Persistence of every log cannot be guaranteed on a crash.

## 10. Detailed test plan

These are tests to IMPLEMENT LATER, not executed results. Prefer parametrized field matrices and independent expected fixtures. Mock only the LAYA boundary for complete flow tests; use spies for dispatcher-call counts and preserve real source extraction/formatting where appropriate.

### A. Gateway invocation and parsing

- A01: valid --hook plus matching payload dispatches exactly once.
- A02–A05: missing, empty, duplicate, or unknown CLI options produce explicit invocation error; no feature runs.
- A06: event argument/payload mismatch fails before dispatch, preserving both values in diagnostics.
- A07–A11: empty stdin, malformed JSON, array, scalar, and null fail parsing/schema validation.
- A12: duplicate hook_event_name or prompt keys rejected; no last-value overwrite.
- A13: reject trailing second JSON object or stdout-style chatter in stdin.
- A14: Unicode including emoji and escaped newlines survives exactly.
- A15: at input limit accepted; one character over rejected; retain existing character-vs-byte budget semantics explicitly.
- A16: deadline bounds a process waiting on unfinished stdin.
- A17: unknown but well-formed event yields unsupported_event without importing/loading LAYA.

### B. Required-field matrix and forward compatibility

- B01: remove EACH required common field independently and assert error stage/field plus zero downstream calls.
- B02: replace EACH common field with null, number, bool, array, object; assert no coercion.
- B03: reject empty session ID/event and whitespace-only identifiers; define string-field emptiness rules in fixtures.
- B04: reject relative/non-string cwd; retain absolute cwd as metadata.
- B05: transcript path need not exist; no transcript read occurs for this feature.
- B06: unfamiliar nonempty permission_mode string survives unchanged.
- B07: extra nested input fields retained unchanged, never automatically sent to LAYA.
- B08: no optional fields present remains valid.
- B09: delete prompt or give it null/non-string values: event-specific failure.
- B10: empty prompt remains valid input and produces the existing expected no-op.
- B11: whitespace/backticks/quotes in prompt unchanged.
- B12: raw payload unchanged after every layer; no shared mutable derived dictionaries across invocations.

### C. Project root and reserved enrichment seam

- C01: identity enrichment changes no values and creates no filesystem/model side effects.
- C02: explicit configured root arrives in feature request with correct provenance.
- C03: missing, relative, nonexistent, or non-directory root fails before feature work.
- C04: nested cwd does not change configured root.
- C05: changed cwd, including a different existing directory, does not silently select another root.
- C06: process working directory differs from event cwd/root; project references still resolve by root.
- C07: injected enrichment output cannot override common fields or configured root; reject an invalid derived object at the boundary. No real future root resolver is implemented for this test.
- C08: fixture has same filename under cwd and root; documented root-based selection is enforced.
- C09: traversal and symlink escape remain rejected by source access policy.
- C10: rendered context paths are project-relative; no unintended machine path leakage.
- C11: root path with spaces/Unicode works, no shell interpolation.
- C12: no git discovery, parent-directory guessing, transcript parsing, or state files added by identity seam.

### D. Three-layer routing and feature results

- D01: exact invocation order: common validation, seam, event validation, handler.
- D02: common validation failure prevents event dispatcher and handler.
- D03: event validation failure prevents handler.
- D04: UserPromptSubmit calls only Prompt Context Enrichment once.
- D05: internal methods never reread stdin or emit protocol stdout.
- D06: Context traverses both dispatchers unchanged until serialization.
- D07: multiple_relevant traverses as Noop with the exact reason.
- D08: typed Failure preserves stage/code; unexpected handler exception is logged as error.
- D09: unknown result variant/missing text/wrong text type/empty context rejected before emission.
- D10: repeated invocations have independent IDs and no duplicated handler registration or model calls.
- D11: real mode absent never imports/loads model; config flags retain current semantics.
- D12: maintain an explicit adapter mapping for every actual flow reason: expected ambiguity/no-match becomes Noop; operational/model/extractor errors become Failure internally. Preserve empty stdout/exit 0 outward behavior. Unrecognized reasons fail explicitly; no substring-based guesses. Record the mapping after inspecting the actual flow in Phase 4.

### E. Protocol and observability

- E01: Context gives exact event envelope, one JSON object, newline, correct escaping.
- E02: Noop gives ZERO stdout bytes and exit 0; assert it is neither `{}` nor `null`.
- E03: handled validation/processing error gives empty stdout/exit 0, ERROR log and stderr diagnostic.
- E04: Python print, native fd1 writes and SDK loading progress remain off stdout on success/noop/error.
- E05: final no-op log has reason, response_present false and byte count zero; no response_prepared/emitted record.
- E06: context byte count uses UTF-8 encoded length, including newline; emoji catches character/byte confusion.
- E07: emission logged only after successful write/flush; broken pipe cannot report emission success.
- E08: common and event logs correlate to the same invocation/session; invalid session logs remain useful.
- E09: logger failure causes stderr diagnostic without altering stdout payload or misclassifying feature outcome.
- E10: new gateway/dispatcher records exclude raw prompt; any existing debug option does not change output. Do not assert that legacy lower-level logs are globally redacted.
- E11: concurrent gateway invocations have distinct invocation IDs and correctly correlated captured records. Characterize shared-file logger behavior separately; cross-process locking/global logger hardening is deferred unless an existing required guarantee is broken.
- E12: replay captures actual stdout independently of response_prepared; missing parsed response is report null, never transmitted JSON null.

### F. Full flow and regression cases

- F01: synthetic TypeScript prompt through actual gateway, dispatcher, flow, helper, formatter with only model mocked; compare manually specified expected context.
- F02: controlled model chooses multiple_relevant; assert no context extraction/emission beyond what the existing flow requires.
- F03: missing/ambiguous file, no candidate, unclear selection, rejected confidence, malformed model response, model timeout and helper timeout each produce their documented outcome.
- F04: selected code, relevant dependencies, partial coverage and source text remain faithful.
- F05: quote/Unicode/path/line metadata examples match the current formatter's agreed root-relative contract.
- F06: input deadline, model-load deadline, prediction deadline and cleanup each remain bounded.
- F07: dependency limits and current final-context warning/send-unchanged policy remain covered; do not restore old truncation/no-op expectations accidentally.
- F08: fixtures/source files unchanged by hook invocation; no session logging database or new persistent state.
- F09: experiment runner, trace collector and IDE launch callers point at gateway after migration; no stale executable invocation.
- F10: repeated subprocesses exercise independent lifetimes and uncontaminated protocol output.
- F11: when supplied, validate plugin registration command syntax and event argument/payload agreement with fixtures; do not require real activation for contract tests.
- F12: one isolated live Claude verification is a later separately reported check, after registration/setup is supplied; subprocess success alone is not harness-delivery proof.

## 11. Existing test debt to reconcile

At the inspected commit, `tests/test_prompt_hook.py` includes expectations of a `Selected TypeScript context (partial)` JSON-text formatter and rejects budgets above 8000 or context exceeding the threshold. The inspected hook now calls `format_context` and treats the final context limit as a warning with send-unchanged behavior. Those tests and the implementation disagree on their face; no suite was run here. The implementing agent must inspect the latest formatter and decisions before correcting tests. Do not simply bless current output by snapshot regeneration, and do not silently restore obsolete behavior during dispatch extraction.

Maintain a migration checklist for every old test: retained, moved, updated with rationale, or replaced by a stronger behavioral check. Include existing flow/source-helper/method-ambiguity tests. This provides coverage for the current implementation as well as the new layers, without claiming an uninspected previous commit was fully tested.

## 12. Top-down phases, tests, and commits

Each phase ends with its own passing commit on the SAME feature branch and PR. Write failing checks locally, implement the phase, then commit code and its tests together after they pass. Do not push deliberately red intermediate phase commits or empty implementation stubs that silently bypass the current hook. Keep the old executable active until the replacement passes the full flow. No application behavior is switched merely to demonstrate an upper layer.

For each phase, update `docs/phases/hook-gateway/phase-NN.md` with base/head SHA, changed files, test IDs mapped to pytest node IDs, commands, actual pass/fail/skip counts, baseline failures, deviations, and remaining dependencies. A test name or green mocked test alone is not evidence of real model/Claude behavior.

### Phase 0 — isolate branch, verify contracts, establish baseline

- Fetch current main and start an isolated worktree/branch using section 16. Record the actual starting SHA. Inspect repository instructions, existing plans, root/formatter PR status and all hook callers.
- Copy this plan into `docs/hook-gateway-plan.md` on that branch. Create the field ledger and flow-outcome inventory; verify current official schemas for the supported CLI version. Schema uncertainty blocks release of that adapter, not unrelated upper-layer tests.
- Run the existing relevant Python/TypeScript tests and record pre-existing failures. Audit formatter/budget test debt against the other agent's ownership; do not repair their files concurrently without agreement.
- Add characterization tests for current successful output, multiple_relevant no-op, and protocol purity using stable fixtures. If a test is obsolete, record the evidence and owner rather than silently changing the expected result.
- **Tests:** scenario S01/S02 baseline equivalents; inventory all A–F IDs. No contract-test changes justified solely by current output.
- **Commit:** `test: establish hook gateway migration baseline` (plan, ledger, characterization tests, evidence).
- **Gate:** baseline is reproducible; any failing existing checks have exact provenance and an assigned resolution. No new failures. Known unrelated failures do not require pretending the suite is green; all affected failures must be resolved before merge.

### Phase 1 — gateway transport and response contract

- Implement the new public gateway with an injected dispatcher for tests. Own stdin decoding, CLI hook-name agreement, invocation ID, input/deadline boundaries, stdout isolation, serialization and the internal result types. Keep lower layers unimplemented in production routing until their phases are ready.
- Validators have precise typed errors. The outer command preserves the documented nonblocking policy. No accidental argparse exit 2.
- **Unit tests:** parser/CLI/result serializer, A01–A15/A17 where relevant; E01–E03/E06/E07; S01/S02/S03/S08/S09/S10 with fake dispatcher. Assert exact JSON or exact empty bytes independently of implementation helpers.
- **Process tests:** A16, E04 and broken-pipe behavior where real process I/O is necessary. Deadline tests use a generous outer timeout, not exact timing assertions.
- **Commit:** `feat: add tested hook gateway transport`.
- **Gate:** focused tests pass; existing active hook still works; no model import from gateway import alone.

### Phase 2 — common ingestion, main dispatch, enrichment seam

- Implement the common envelope, contract-based required fields, explicit event registry, immutable-by-contract raw payload, identity enrichment and correlated gateway logs.
- Use an injected fake event dispatcher. Unknown event handling requires only a valid matching name pair, never UserPromptSubmit-only fields, project root or model configuration.
- **Unit tests:** B01–B08/B12, C01/C07/C12, D01/D02/D05/D10, E05/E08–E11; S03/S04/S05/S11/S12. Spy assertions check downstream calls are zero after failure.
- **Commit:** `feat: validate and dispatch common hook input`.
- **Gate:** no silent defaults for required fields; optional fields handled per ledger; no new side effects from enrichment; all Phase 1–2 tests pass.

### Phase 3 — UserPromptSubmit dispatcher

- Implement event-specific prompt ingestion, metadata logging and one typed request to one injected feature handler. Only this layer understands prompt-specific fields.
- Carry project configuration as an explicit dependency. Generic dispatch must not reject other event names because this feature lacks a root.
- **Unit tests:** B09–B11, D03–D06/D08/D09, relevant E08/E10, S06/S07/S11/S12. Exercise Context/Noop/Failure propagation with a fake handler and exact one-call assertions.
- **Commit:** `feat: add tested user prompt submit dispatcher`.
- **Gate:** all Phase 1–3 checks pass; feature behavior remains isolated; prompt/raw payload are unchanged.

### Phase 4 — Prompt Context Enrichment adapter

- Extract the old executable's feature behavior behind the named handler; call the existing flow and formatter through their actual API. Retain model opt-in, selection rules and budgets.
- Resolve explicit root configuration and outcome mapping here. Consume the other agent's reviewed root API after integrating its merged changes. Do not implement duplicate root/formatter helpers. If it is unavailable, retain a clear dependency and complete adapter unit tests with fakes; do not mark real integration complete.
- **Unit tests:** C02–C06/C08–C11 at the adapter boundary; D07–D12; S01/S02/S08/S13–S16. Fake flow and formatter independently. Assert formatter is not called on no-op/error, context formatted once on success, correct root/config forwarding and no model load when disabled.
- **Regression tests:** current flow's existing question/rule/extraction tests and budget tests; F03–F07 when dependencies are available.
- **Commit:** `refactor: extract tested prompt context enrichment handler`.
- **Gate:** API ownership settled, outcome mapping explicit, no accidental model-policy change, all accumulated affected tests pass.

### Phase 5 — full wiring and caller migration

- Connect actual gateway → main dispatch → event dispatcher → feature. Update experiment/IDE callers and trace reports. Remove old executable only if all callers are migrated; otherwise keep a forwarding wrapper with a documented retirement condition.
- **Integration tests:** F01–F10, E04/E12 and all S01–S16 through the appropriate boundary. Use real helper/flow/formatter with only LAYA mocked for full-flow fixtures. Unit tests remain separate and do not need Node/MLX.
- Assert the old wrapper, if retained, delegates once and yields the same bytes/configuration; no second pipeline. Capture stdout/stderr independently of application logs.
- **Commit:** `refactor: route hook callers through the shared gateway`.
- **Gate:** full relevant Python and TypeScript suites pass or documented unrelated baseline failures are reviewed; no affected failures, stale launch paths, swallowed validation failures, or missing planned assertions. No normal-session hook activation.

### Phase 6 — final test audit and PR readiness

- Map every A–F/S test ID to a real test and assertion, not just an unchecked checklist. Expand grouped IDs (A02–A05, A07–A11) and field matrices into listed parametrized cases. A behaviorally equivalent existing test may satisfy an ID if its assertion is identified.
- Require boundary/error paths, current implementation regressions and all in-scope scenarios. Categorize unit, subprocess, integration and live checks; mark plugin/live dependencies deferred explicitly.
- Audit scope and the final PR diff against this plan. Run tests again after any merge/conflict change that affects them; final candidate must have current CI/required checks. Avoid repeatedly rerunning unchanged suites without cause.
- **Commit:** `test: complete hook gateway coverage and migration evidence` (real missing tests/fixes and evidence; no empty commit required).
- **Gate:** test coverage ledger complete, no unreviewed deviation, current main integrated under section 16, PR ready for merge. If plugin assets are absent, merge scope is application gateway only and installation remains explicitly unfinished.

### Phase 7 — plugin setup, conditional follow-up

- Once Sharon supplies plugin assets and installation preference, validate actual commands and update README installation, disable and debugging instructions. Do not stall Phases 0–6 on these missing inputs.
- **Tests:** F11; isolated F12 only when setup/environment is available and authorized. Contract fixtures do not count as live delivery.
- **Commit:** `docs: document verified hook gateway plugin setup`, with registration tests and supplied-asset changes if in scope.
- If assets arrive before merge, include this phase in the same branch; otherwise use a follow-up PR from then-current main. Do not leave the application PR indefinitely open solely for installation preferences.

Acceptance: one public entry, three layers, precise schema failures, explicit root provenance, no duplicated lower-level policy, one handler, one JSON response or zero bytes, observable no-op/error distinction, independently asserted unit scenarios, and all in-scope tests recorded per phase.

## 13. Pending inputs and deferred work

Pending from Sharon: plugin directory, plugin JSON, hooks JSON, preferred launch/install approach. Ask for setup preference when that work becomes actionable; it is not needed to finish this plan.

Deferred: additional hook adapters and their field contracts, future envelope enrichers, filters, multi-handler evaluation/composition, YAML rules, Stop recovery, retry/session state, new model selection policies, and broader hook registration. Keep interfaces ready for growth without implementing these now.

Reference for implementation-time contract verification: https://code.claude.com/docs/en/hooks (common input fields, event-specific input and JSON output). This plan's code observations come from current repository reads; refreshing the official page during this planning turn returned an error. Recheck official event contracts against the supported CLI version before registration.


## 14. Critical review: weaknesses and adopted refinements

1. **The original sequence was not a phased delivery plan.** It mixed transport, event adaptation, source behavior and caller migration. Revision 2 assigns explicit commits and test gates from gateway down, keeping the old active path intact until Phase 5.
2. **Root handling overlapped another agent's work.** Replacing cwd semantics inside this PR could duplicate or undo their fixes. This branch owns gateway/dispatch/adaptation; the other branch owns source-root/formatter semantics. Integrate their reviewed API and test the boundary. Never use parameter renaming as a substitute for agreeing on semantics.
3. **Requiring every fixture field could break valid events.** Required fields must have a documented or feature-required reason. Phase 0 produces a field ledger; optional metadata is validated when present. Strictness means no missing required input or bad types, not rejecting all unknown/unused fields.
4. **Validation failure was confused with process blocking.** Internal Failure and ERROR logs are mandatory; current command-hook exit 0 remains intentional. Unit tests assert Failure directly, subprocess tests assert protocol behavior. An integration test that checks only exit 0 is insufficient.
5. **Unknown-event routing was ambiguous.** Validate JSON and the event-name pair first, then look up the contract. Unsupported event returns no-op without requiring this feature's prompt/root metadata or loading its dependencies.
6. **The service abstraction could grow into unnecessary infrastructure.** Use a small typed dependency bundle or explicit function arguments for logger, flow, formatter and configuration. No DI framework, dynamic plugin loader or general rule engine. Three layers need not imply three processes or a subprocess per layer.
7. **Tests were numerous but their oracle and level were unclear.** Add the scenario catalog below; hand-author expected values and control fake boundary results. Do not calculate expected output using the production serializer/formatter being tested. Unit tests must run without MLX, model downloads, Node or Claude. Full-flow tests retain the real TypeScript helper and mock only the model boundary.
8. **Logging promises exceeded the existing logger.** New records are correlated and metadata-only, but old lower layers may log prompts and append semantics may have concurrency limits. Avoid an unrelated global logger rewrite. Report those limits accurately. Do not claim stdout byte counts equal Claude receipt, or claim zero bytes after a potentially partial failed write: record unknown/partial when necessary.
9. **Budget and formatter tests were stale.** Preserve approved behavior from current main/the other PR, not historical assertions or an automatically regenerated snapshot. Resolve ownership and product intent before updating expected output.
10. **Multi-handler growth was over-specified.** Keep a single handler call behind the event dispatcher and one internal result union. Multiple actions, priorities and merging remain future work. Reserve only stable seams that current code actually needs.
11. **The original plan implied all checks could finish before plugin assets arrived.** Core application readiness and installation/live verification are separate gates. Explicitly defer unavailable checks without presenting them as passing.
12. **Exception classification could swallow genuine failures.** Make the flow-reason mapping explicit, reject unknown result forms, and catch errors once at the outer boundary. Logs must distinguish handled error, expected no-op and unsupported event. Do not infer error classes by arbitrary substring matching.

## 15. Required unit scenario catalog

Each row below is a concrete unit scenario. Implement using fresh fixtures and injected fake dependencies; assert returned result, dependency calls and log metadata. Add parametrized type/missing-field coverage from A–F rather than repeating only happy paths.

- **S01 Accepted context:** valid event, fake flow returns accepted context, fake formatter returns a fixed string. Expect Context, flow once, formatter once; gateway serialization tested separately against literal JSON.
- **S02 Multiple relevant:** fake flow returns the actual multiple_relevant result. Expect Noop with exact reason, formatter zero calls; gateway serializes to zero bytes. The captured real replay is background evidence, not a deterministic model oracle.
- **S03 Missing session:** omit required session_id. Expect field-specific Failure before event/feature calls; invocation ID still present in error record.
- **S04 Mismatched event:** argument UserPromptSubmit, payload Stop. Expect event_mismatch before event contract or model access.
- **S05 Unsupported event:** matching unknown event names and minimal JSON. Expect unsupported_event no-op without requiring prompt, root or UserPromptSubmit metadata.
- **S06 Missing prompt:** otherwise valid envelope, prompt absent. Expect UserPromptSubmit validation failure, handler zero calls.
- **S07 Empty prompt:** prompt is empty string. Expect a valid typed request preserving the string; fake handler returns no-match. It must not be confused with missing prompt.
- **S08 Operational failure:** fake flow raises an error or returns each recognized failure reason. Expect Failure, no formatter, error stage/code retained; outer protocol remains nonblocking.
- **S09 Bad handler return:** null, object with unknown variant, Context with non-string/empty text. Expect invalid_result Failure, never serialize null or malformed output.
- **S10 Unicode context:** context contains emoji, quotes, backslashes and newlines. Expect reversible JSON encoding and correct byte count including newline.
- **S11 Extra fields:** raw payload has unknown nested metadata. Expect retained raw object, no mutation and no metadata forwarded to LAYA as prompt text.
- **S12 Repeated calls:** same session, two invocations. Expect distinct invocation IDs, separate derived state, one handler call per invocation, no cached outcome leakage.
- **S13 Missing root:** valid event but missing required feature configuration. Expect configuration Failure before source/model access; unsupported event still unaffected.
- **S14 Root/cwd separation:** root differs from raw cwd. Expect raw cwd preserved and the agreed root API given configured root with provenance. Test against the other agent's final API, not a guessed parameter convention.
- **S15 Model disabled:** explicit real opt-in absent. Expect the agreed disabled outcome with no SDK import/load/predict; preserve current external no-output behavior.
- **S16 Formatter failure:** flow succeeds but formatter throws. Expect formatting Failure, no Context emission; distinguish it from method-selection failure.

Cross-cutting assertions: no hidden filesystem/network/model activity in units, no stdout from internal methods, errors stop dependent calls, logs and output are independently asserted. Use deterministic fake clocks for duration metadata; reserve real timeouts for subprocess tests. A unit test calling a real model is an integration test and must not hide in the fast suite.

Coverage ledger format: test ID; phase; test level; fixture/input; expected outcome and source; actual test node/parameter; key assertions; result; deferred reason if any. Every in-scope ID must be mapped before merge. No coverage percentage substitutes for missing critical scenarios.

## 16. Parallel work, branch, PR, conflicts and merge

This section governs the future implementation by Sol. It does not request repository changes during this planning turn.

### Start safely from current main

1. Read repository instructions and inspect git status, remotes and worktrees. Leave the other agent's files/index/branch untouched. Never stash, reset, clean or checkout over their work.
2. Fetch origin. Create a NEW branch, e.g. `feat/hook-gateway`, from fetched `origin/main` in a separate worktree. Use a unique suffix if the branch/path already exists. Record base SHA and branch ownership. Do not start from a stale local main or another agent's unmerged branch.
3. Inspect open PRs/recent commits for overlapping paths and contracts. Record the root/formatter owner's PR/branch and expected API. Shared high-risk paths include the old hook, formatter, flow, tests, experiment runner and README. A clean textual merge does not prove semantic compatibility.
4. Make the Phase 0 commit, push the feature branch, and open ONE draft PR targeting main with planned scope, phase checklist, baseline and dependencies. All subsequent implementation commits go there. No direct main commits/pushes.

### During implementation

- Commit each completed phase with its tests and evidence. Push ordinary branch commits and update the PR checklist/description to describe the final work, not abandoned approaches.
- Check for new main changes before touching overlapping files and at phase boundaries where another PR has landed. Reuse newly merged fixes; do not copy another agent's unmerged changes into this branch without documenting dependency and ownership.
- Prefer merging fetched origin/main into this shared feature branch over rebasing published commits. Do not force-push or rewrite another agent's work. Follow required repository branch policy where it differs, documenting the adjustment.
- If the root API dependency is pending, complete upper-layer phases and tests. Do not wait indefinitely or implement a competing root solution. Report the exact blocked phase and dependency.

### Conflict handling and Astra escalation

- **Very simple mechanical conflict:** whitespace, a non-overlapping documentation insertion, or import ordering with one obvious resolution. Sol may resolve it, inspect the diff, rerun relevant checks, and tell Sharon which files conflicted and how they were resolved before merge. Do not auto-resolve using blanket ours/theirs.
- **Any conflict requiring semantic reasoning:** input contracts, root/security behavior, output format, error mapping, config precedence, test expectations, or another agent's implementation. Spawn an **Astra model agent** before choosing the resolution. Supply base/main/feature SHAs, both diffs, this plan, related PRs, failed tests and the exact competing behaviors. Ask for analysis, recommended resolution, required tests and any plan adjustment.
- Astra records its rationale and updates the plan/coverage ledger on the feature branch (or returns an exact patch to Sol). Sol implements the reviewed resolution and verifies it. Keep the review focused on the conflict, not a full unrelated redesign.
- **Major conflict or user decision needed:** incompatible product behavior, changed scope, unclear intended semantics, permission/security changes, risk of discarding another agent's work, or repeated unresolved failures. Notify Sharon immediately, explain the alternatives and Astra recommendation, and pause merge/affected edits for his decision. Continue independent safe work if useful. Elapsed time is not approval.
- If Astra is unavailable, report the unresolved reasoning-dependent conflict; do not silently replace the required review with guessing. Avoid endless retries: after a reviewed resolution still fails materially, report the blocker rather than repeatedly changing policy or weakening tests.
- Textually clean but semantically incompatible changes follow the same escalation policy. All conflicts, including simple resolved ones, are summarized to Sharon before merge; only those needing his decision require a response.

### Final integration and merge

1. Fetch current main, integrate it on the feature branch, inspect all combined changes and check for unresolved conflict markers and semantic overlaps. Record the tested main and feature SHAs.
2. Run affected tests after each conflict resolution and full required checks on the final candidate. Review the A–F/S coverage ledger and plan deviations. Passing stale CI on a previous SHA is insufficient.
3. Update the PR to ready with concrete behavior, validation evidence, deferred plugin/live work and conflict resolutions. Respect repository-required reviews and CI. Preserve separate phase commits where repository policy permits; if squash is required, retain the phase/evidence history in the PR and report that choice.
4. Report conflicts and any major unresolved issue to Sharon before merging. If there is no unresolved decision and checks/reviews pass, merge under this requested workflow without asking routine permission again. If main changes again, integrate/retest or use the repository's verified merge queue; never force a stale merge.
5. Confirm the PR is merged and report PR URL, merge SHA, test outcomes, deviations and remaining installation tasks. Do not claim a live hook was enabled by merging application code. Keep worktree cleanup scoped to this agent's clean worktree only.

## 17. Handoff to Sol

Implement this revised plan top-down, one passing phase commit at a time on a dedicated branch/PR from current main. Re-read live repository state before starting. Use unit fakes at each unfinished lower boundary, preserve the existing active hook until full integration, and consume the other agent's root/formatter work. Maintain the field ledger, outcome mapping and test-ID coverage ledger. Escalate semantic conflicts to Astra and material decisions to Sharon. Plugin setup remains conditional on supplied assets/preferences. Report actual results rather than treating planned tests as completed.

Revision-2 review is a design review, not verification of code or executed tests. The latest main tree observed during refinement remained `91ec04b1b3f74cf6c41da530d7b00c7ca34d8ef5`. The official-doc lookup again failed; Phase 0's schema-source verification remains explicit. No implementation branch, PR or application commit was created by this refinement.

## Implementation progress (partial)

Phases 0–3 implemented on feat/hook-gateway, draft PR2, with separate tested commits and Astra-reviewed deviations D01–D06 in phase evidence. Phase4 contains independently tested preparation/result-mapping helpers and an explicit root_api_unavailable error boundary. It does not run real selection. Phases5–7 are not completed. The active hook/callers remain unchanged. Official schema verification and the reviewed root-based resolution API remain hard integration/release gates. See docs/phases/hook-gateway for actual test evidence and partial coverage ledger. Do not merge this unfinished replacement or interpret its passing unit tests as live context delivery.


## D07/D02 amendments after merged-root clarification

The separate root-flow API dependency was inferred incorrectly. The merged root/formatter/navigation work is already in main. This branch now owns the narrow explicit resolve_from_project_root opt-in reviewed by Astra. Legacy flow/resolver callers retain defaults; new gateway calls root mode with raw cwd retained separately. This replaces earlier waiting/ownership language wherever inconsistent.

Structural schema verification uses official Anthropic SDK source pinned at https://github.com/anthropics/claude-agent-sdk-python/blob/1ea8cb74ddcdadbfaa9b20dfa8268e18047851e7/src/claude_agent_sdk/types.py . This resolves D02 for core schema; live installed CLI/registration/receipt remain Phase 7 checks. Required transcript_path fixtures and matrices are updated.

The temporary root_api_unavailable handler is removed. Gateway invokes the real selection flow, existing helper and formatter. The old hooks/user_prompt_submit.py path is a forwarding wrapper only, retained until Sharon supplies final plugin bindings and external callers can retire it. Replay/IDE experiment callers use the shared gateway through the updated experiment runner.


## Final core status (supersedes historical partial checkpoints)

Core Phases 0–6 are complete. Final committed source/test candidate 23eb571ffc8411aef0b78f3ac7a31a015dba8e0f passed795 Python tests(3 existing skips) and122 TypeScript tests. All91 implemented IDs map to passed JUnit cases with explicit assertions and expected-source metadata. Conditional plugin/live F11/F12 remain deferred. The inferred root API dependency is resolved by Astra-approved explicit root mode; SDK structural verification is pinned and required transcript input is implemented. No real model/Claude session/plugin activation is claimed. See docs/phases/hook-gateway/phase-06.md for final independent review and merge gates.
