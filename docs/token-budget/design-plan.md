# Current PR23 contract

Ordinary `predict()` remains compatible and does not perform budget inspection; the SDK may retain its existing truncation behavior. Use `predict_strict()` for pre-inference inspection and rejection. Supplying an inspection provider alone does not enable strict mode.

`strict=True` is available on the shared QuestionBlock/Block runtime, ticket_triage, ticket_triage_v2, requested_action and context_scope. Method selection (legacy and V2) and all flows remain exactly as main and do not expose strict selection. Existing experiments remain exactly as main; the only new experiment files are the seven manual `experiments/tokenizer_smoke/` scripts/documentation. Requested action retains main's default temperature 1.0 and explicit caller overrides.

Limits are centralized in `laya/model_limits.py` with source URLs, review date and periodic review guidance. New models require explicit entries. Strict mode counts with the loaded tokenizer; source/package/tokenizer-file hash gates and copied tokenizer assets are removed. Managed loaded-object integrity checks remain. CODE is still a refused candidate.

Unit tests use mock tokenizers and establish accounting/control flow only. Actual tokenizer parity and live Mac compatibility remain unverified. Sharon runs the manual local-checkpoint smoke cases; no live model, download or campaign is part of this change. Raw token-budget evidence is excluded from the PR tree.

## Historical record (superseded where inconsistent above)

# LAYA strict token-budget validation — design and implementation plan

Date: 2026-10-31  
Status: historical design with implementation through increment 10; the user-directed mock-only cleanup below supersedes its former real-fixture testing requirements.
Revision: small TDD commits, mandatory Astra recovery, and baseline preservation.  
Scope: English requests and TypeScript source content within the existing application architecture.

Research: [laya-token-budget-research-results.md](research-results.md).


## Current user-directed scope (supersedes historical testing requirements)

The latest explicit instruction is to keep unit tests mocked: do not call a real tokenizer or SDK, and remove the entire token-budget fixture bundle and preparation tooling. The current suite uses controlled token IDs/runtime doubles and hand-specified assembly/accounting expectations. It does **not** establish real-tokenizer or upstream SDK parity. Earlier real-fixture mandates, parity gates, and instructions against removing those fixtures below are historical and no longer govern this cleanup. The removed raw execution logs remain in Git history; only concise current validation summaries belong in the final tree.

Unpublished increment 11 was preserved separately and is not part of this cleanup. No experiment edits/runs, main integration, or production inspection redesign are authorized in this step. Production loaded-tokenizer verification remains unchanged. Experiment cleanup and runtime/hash simplification remain pending. See [testing.md](testing.md).

## 1. Decisions carried into this design

LAYA owns tokenization, per-model configuration, validation, and diagnostics. Building blocks pass exceptions unchanged. Only the flow may decide to shorten, retry, choose a different block, or skip.

Any input that the supported SDK would truncate must be rejected before prediction inference. This includes instructions, rendered choices, shared-head allocation, state, and final sequence trimming. A total-token check alone is insufficient.

Use a typed exception with a JSON-serializable report. Successful predictions retain their existing response shape. No error object is passed into ordinary answer validation.

Sharon identified the existing flow as a sandbox, then explicitly required preservation of existing valid behavior and Astra's decision on any failure. The later instruction governs: sandbox status does not authorize ignoring a failed test or changing its expectation independently. Formerly truncated requests must still be rejected as already required, but any existing-test failure caused by that intentional change must go to Astra before its fixture or expectation is changed. Explain the outcome to the next agent; never weaken the token guard to restore a misleading success.

The initial guarantee covers verified model/runtime profiles and managed prediction calls. Arbitrary mutating SDK hooks are outside that guarantee and must produce an explicit unsupported-inspection error when encountered through the guarded path.

This design changes neither question wording nor answer-selection rules. It introduces no automatic shortening, chunking, retries, model fallback, or larger context settings.

## 2. Current flow inventory

Checked main at `83211fd88d10e4c0854797dec47df33ce8d04ea5`.

There is one implemented main flow module: [file_method_context.py](https://github.com/SharonLanger/laya-context-router/blob/83211fd88d10e4c0854797dec47df33ce8d04ea5/src/laya_context_router/flows/file_method_context.py). The other file in that flows directory is its package initializer.

The flow accepts a narrow request shaped like “Explain `src/example.ts`: how does this work?”. It resolves one production TypeScript file, extracts its callable outline, asks the method-selection block to choose a relevant callable, and collects the implementation plus bounded related code. It returns context or an explicit no-op reason. It also has an optional second method-selection attempt for one undecided case.

The prompt-submit integration calls this same flow. It is not a second independent flow. Requested-action, context-scope, and method-selection are building blocks, not separate composed flows.

The existing flow catches ordinary prediction exceptions and returns a generic `model_error`. It can retain that behavior for now. A structured budget ERROR log will already have been emitted at the shared boundary. Future flows can catch the typed budget exception and inspect its report directly.

No flow redesign, fallback adjustment, or hook reason-map migration is required in this feature. Add a concise migration pointer near the existing generic exception handler so a later agent knows why details are present in the LAYA log even when this sandbox flow returns a generic error.

## 3. Ownership and change boundaries

The shared `src/laya_context_router/laya/predict.py` function is the single application enforcement point. Both block runtimes already use it.

The implementation should remain concentrated in the LAYA package:

- `laya/budget.py`: report definitions, error types, and orchestration of inspection.
- `laya/budget_profiles.py`: immutable supported model/runtime profiles.
- `laya/budget_adapters.py`: version-specific normalization, rendering, and exact accounting.
- `laya/predict.py`: invoke inspection, log, reject or continue.
- `laya/registry.py`: associate a lazily loaded agent with its inspection capability.

These are proposed module names, not existing files.

Building-block preparation, reducers, questions, and confidence rules retain their behavior. Block runtimes need only explanatory comments/documentation if useful; they must not catch budget errors to invent a block-level recovery result.

Test fixtures and the live-check capturing wrapper may need explicit inspection-capability wiring. That is infrastructure compatibility work, not new token logic in blocks.

Keep the existing language/runtime architecture. “English and TypeScript” describes the supported input corpus; this feature is not a rewrite of the existing Python LAYA boundary.

## 4. Profile and lazy-loading policy

### Model facts

| Profile | Sequence limit | Head parameter | Initial option-text cap |
|---|---:|---:|---:|
| aac6fef/laya-typed-decisions-mlx | 1,024 | 256 | 48 |
| tindang/laya-code | 512 | 192 | 48 |

Exact checkpoint revisions and tokenizer fingerprints are recorded in the research report. The 48-token rule belongs to the inspected runtime. Encoder/tokenizer metadata showing 8,192 does not replace these effective limits.

Profiles record model ID, expected checkpoint identity, supported runtime identity/version, tokenizer and tokenizer-config fingerprints, default limits, and the adapter's sequence-rule version. Static definitions in one module are enough. Do not introduce a remote configuration service or fetch metadata on every prediction.

Verify a real agent against its profile once when loaded. Resolve identity from actual loaded metadata; do not label requested settings as observed facts. The requested canonical ID selects the profile. Observed model_id may be that ID or an existing local directory strictly resolving to the same observed model_dir; record both requested and raw observed identity. Local-path binding never substitutes for actual pinned revision and all fingerprint/runtime checks (Astra D002). The runtime qualification must match the inspected sequence-building semantics, not merely a loosely compatible package version. A mismatch is an explicit inspection failure, never permission to continue unguarded.

Keep agent and tokenizer loading lazy and invocation-owned. Repeated calls reuse them. Do not add a cache keyed by arbitrary request text. A rejected request need not invalidate a correctly loaded agent. Failed capability initialization must not leave an agent considered verified.

The existing model/temperature/language registry key may remain while profiles are immutable within an invocation. If runtime, revision, or budget overrides become selectable configuration dimensions, include them in reuse identity before exposing them. No new per-call budget override API is required in the first version.

### Code-model readiness

The code model's tokenizer and limits are researched, but full MLX execution has not been verified. Keep its profile as an explicit candidate until the intended runtime passes load/encoding validation. Do not silently route it through a different package based on its name.

The budget interface should permit another runtime adapter without changing blocks. A separate upstream-LAYA backend or broader model-routing feature remains a distinct implementation task if actually needed.

The current MLX profile can be developed and tested independently. Supporting the code model in production must not be claimed merely because tokenizer parity passed.

## 5. Inspection and prediction lifecycle

1. Validate the request's existing question contract. Preserve malformed-input errors.
2. Create a private snapshot of both state and questions after block preparation. Preserve strings, dictionaries, and conversation lists already accepted by the direct prediction path; match SDK serialization and its state-type-dependent truncation direction. Use the same content and question order for inspection and prediction. Do not count a template before dynamic criteria are inserted.
3. Resolve the lazy agent and its verified inspection adapter.
4. Verify that this managed call uses the expected immutable configuration and no unsupported SDK input-mutating hooks.
5. Inspect all questions against the shared state. Generate a complete report before any question is sent to prediction inference.
6. If inspection is unavailable or unsafe, log and raise the appropriate inspection error. Never report the request as fitting.
7. If any content would be trimmed, log one structured budget-rejection event and raise the typed overflow exception.
8. Otherwise call the agent's normal prediction method with the inspected request snapshot. Preserve existing response validation and copying.

A rejected multi-question request produces no partial answers. One question failing is enough to reject the entire call, but the report should identify all measured violations.

One application checking location may perform several component encodings. The SDK may encode again during `predict`. For the first version, matching the pinned, deterministic SDK behavior is preferable to inventing a new inference entry point. A later optimization may reuse prepared IDs if a verified interface supports that.

An optional inspection-only method may expose the same inspector through the LAYA service/registry. It returns the report without prediction. It must not duplicate logic or move the check into blocks. A later prediction always rechecks its actual request; a previous inspection is not a reusable authorization token.

## 6. Exact accounting rules

Use the selected checkpoint tokenizer with matching normalization and special-token settings. Never substitute characters, words, another model's tokenizer, or a 90% total-budget heuristic.

The adapter must reproduce the SDK's separate component encodings:

- Instructions include the question-type prefix.
- Choice text includes the actual rendered label and description.
- Score and boolean questions use their SDK-specific rendering.
- Literal mask-token replacement matches the SDK.
- Leading spaces, separators, classification tokens, and option markers count exactly where the SDK adds them.

Track the following stages without actually shortening the request passed by the application:

1. Unrestricted token IDs for instructions and each rendered option.
2. First option-text cap of 48.
3. Shared-head allocation and its marker-inclusive per-option span cap.
4. Remaining instruction allowance.
5. Assembled head length including structural tokens.
6. Per-question state allowance after reserving the final separator.
7. Final sequence slice and surviving marker positions.

The head parameter is an allocation input, not a literal maximum for the assembled head. Do not reject solely because assembled head length exceeds that parameter; reject when one of the actual SDK operations would lose content or required structure.

For each slicing operation, compare the stage's incoming tokens with its retained tokens. Report stage-local loss and separately compute the final retained content. Do not add overlapping loss measurements into a misleading total.

Also record the untrimmed full sequence length. If it exceeds the overall limit, expose that constraint even when earlier head cuts would make the final SDK sequence smaller. Label it as a full-request requirement, not a second independent set of dropped tokens.

For several questions, state content is shared but its allowance differs by head. Report each sequence independently. SDK aggregate `usage.input_tokens` is not a per-sequence limit.

The adapter must be qualified against the real SDK builder and cached path. Golden count fixtures alone are insufficient if the implementation and fixtures accidentally share the same mistake.

## 7. Error and report contract

Define a common `InputBudgetError` family with a JSON-safe report and specific stable codes:

- `INPUT_TOKEN_BUDGET_EXCEEDED`: inspection succeeded and predicts content/structure loss.
- `TOKEN_BUDGET_INSPECTION_UNAVAILABLE`: missing profile, unsupported agent/runtime, or missing verified metadata.
- `TOKEN_BUDGET_INSPECTION_FAILED`: an unexpected problem prevented reliable inspection.

A typed subtype such as `InputTokenBudgetExceeded` distinguishes overflow. Keep the error family separate from `ResponseError`, which describes unusable SDK output. Preserve timeout behavior and loader errors.

The report contains:

| Field | Meaning |
|---|---|
| schema_version | Version of the diagnostic contract |
| code, message | Stable classification and short explanation |
| request_id | Correlation ID for this attempt |
| phase | pre_inference |
| request_inference_started | false for these rejections |
| model | Requested ID, resolved revision, runtime and adapter identities |
| tokenizer | Relevant fingerprints/version |
| limits | Effective values and their provenance |
| inspection_status | complete, unavailable, or failed |
| questions | Per-question measurements and allowances |
| violations | Every established offending boundary |
| hint | Migration pointer and concise next-agent guidance |

Each violation identifies the boundary, question ID, option key/index if applicable, incoming/required count, limit, retained count, unit, and processing stage. Required and retained counts must be distinguished from post-inference usage.

Unavailable inspection must use unknown/null measurements rather than zero counts. A report for an unknown profile must not contain a fabricated “within budget” result.

Use strings, finite numbers, booleans, nulls, lists, and mappings only. Expose a stable snapshot of the report so later consumers cannot alter the already-logged evidence. No tokenizer object, exception object, raw source text, or model tensor belongs in it.

The exception message should identify the first actionable violation and request ID. The report holds the full list. Do not claim that retrying the same payload will help.

## 8. Logging and hints for the next agent

At the shared LAYA boundary, log a structured ERROR event before raising an input-budget error. Attach the report explicitly to `details`; the existing logger does not serialize custom exception attributes automatically.

Successful inspection may produce a DEBUG measurement event. Keep normal successful response shape unchanged. Avoid duplicating full prompts/code in the budget report; existing request logging is a separate policy. Handle budget errors separately from the generic prediction-error catch so each rejected request has one authoritative structured budget ERROR event rather than duplicate boundary errors.

Do not let best-effort logging failure allow prediction or replace the intended budget error. Preserve the existing timeout/deadline propagation: a genuine deadline TimeoutError still propagates and never permits inference.

Before integrating enforcement, write `docs/token-budget-migration.md` in the repository. Add a pointer in boundary/error documentation and near the sandbox flow's generic exception handler. The implementation handoff must include this explanation:

> Strict input-budget validation now rejects requests that LAYA previously shortened silently. A failure observed during a building-block call can originate in the shared LAYA prediction boundary. Building blocks intentionally pass this exception unchanged. Find the matching budget ERROR event using its request ID and inspect the named question, option, and boundary. Shortening state does not fix an oversized instruction or option. The existing file_method_context flow is a sandbox and may return generic model_error. Do not disable validation, silently trim input, or increase model limits just to restore an old sandbox expectation.

Include separate guidance for inspection-unavailable failures: verify the adapter/profile and installed runtime, rather than guessing that the text is too long.

If a sandbox or any other existing test fails, stop and ask Astra to classify it and prescribe recovery before changing its expectation or fixture. This also applies when strict rejection appears to explain the failure. Preserve assertions unless Astra documents a specific obsolete expectation and supplies equivalent or stronger replacement coverage. Never delete a suite, weaken assertions, add blanket skips/xfails, disable validation, change confidence rules, or raise limits to obtain green results.

## 9. Custom loaders, mocks, and concurrency

Existing injected agents may implement only `predict`. The new boundary must not assume every object exposes MLX internals.

Add optional keyword-only inspection-provider injection to registry construction and the direct custom-loader path. Preserve get_agent(config) returning the original agent, the existing loader(model, **load_kwargs) calls, and prediction argument/keyword behavior. A supplied registry owns its loader and inspection provider; reject conflicting independently supplied configuration clearly. A provider can supply a verified adapter for a wrapper or a controlled test double for plumbing tests. The live-check capturing wrapper must forward actual verified inspection capability as deliberately as it forwards prediction; requested model IDs alone do not verify a wrapper.

Wire fixtures, offline examples, and capturing wrappers before enabling enforcement. Keep their existing assertions. An opaque predict-only custom agent cannot simultaneously remain unmodified and provide verified strict inspection; document the precise optional-capability migration. Do not disguise this constraint with a default fits report, automatic mock detection, or a real=False bypass. Default offline examples must continue to run without importing MLX or downloading model weights.

No production flag may bypass validation. Tests may inject controlled reports to test orchestration, but those tests must be labeled as plumbing tests; real-tokenizer parity coverage remains required. Test doubles must not be selectable through ordinary production configuration.

Preserve the SDK's tokenizer synchronization rules. Keep the managed request snapshot and configuration stable for inspection and prediction. SDK hooks that can rewrite input are unsupported in this first path. Concurrent external mutation of an SDK agent is outside the managed contract; do not advertise a guarantee for it.

A model load may happen before inspection and can allocate weights. The guarantee concerns this request's inference, not zero startup work. Compile warmup and runtime activation are separate from request inference and must be identified honestly in live evidence.

## 10. Compatibility policy

Unchanged for supported requests that fit:

- Existing prediction success JSON and answer validation.
- Building-block input/output structures and reducer behavior.
- Confidence rules and task-selection semantics.
- Lazy loading and agent reuse.
- Ordinary loader, timeout, and malformed-input exceptions where applicable.

Intentional changes:

- Previously trimmed requests raise a budget exception.
- Unsupported real inspection paths are explicitly refused.
- Injected test/custom agents must provide an inspection capability.
- Some sandbox scenarios may now return generic model_error or fail earlier.

Existing character caps remain independent resource checks. They are not the token guarantee and need no removal in this feature.

Core correctness, transparent block propagation, accurate diagnostics, and unchanged valid behavior remain acceptance gates. Existing sandbox tests remain in the regression suite. Formerly truncated success is intentionally replaced by refusal, but the implementation agent may change an existing expectation only under Astra's recorded instructions.

## 11. Test plan

### Exact tokenizer and sequence parity

Use the pinned checkpoint tokenizer files and SDK builders without weights where possible. Cover English prompts and TypeScript identifiers, signatures, comments, punctuation, and mixed text. Compare token IDs and marker positions, not only lengths. Include fitting and overflowing dictionary/list state, list-state left-truncation accounting, option_order, structured criteria and custom boolean labels where the existing API accepts them. Preserve existing malformed-input rejection rather than expanding accepted schemas incidentally.

Verify direct/cached builders, repeated calls, model switches, and tokenizer configuration identity. Test concurrency under the intended adapter synchronization.

### Boundary tests

For every boundary, cover below, exactly at, and above the effective limit:

- Initial 48-token option text cap.
- Shared-head option redistribution.
- Instruction allowance.
- State allowance.
- Final sequence/marker preservation.
- Untrimmed full-sequence requirement.

Include the reproduced counterexample: a 105-token full request with an 83-token option must fail because that option would be cut to 48. Include a long instruction with short state and an empty-state request whose choices alone overflow.

Test two or more questions where one fits and another does not. Assert the complete violation report and zero calls to prediction/forward for the entire request.

### Boundary, blocks, and flow consumer

Use both existing block runtimes and a minimal test flow that catches the typed error. Assert identical diagnostic contents reach that flow; no enrichment or reduction occurs for the rejected request. The test flow observes the error without inventing retry policy.

The existing sandbox flow may continue mapping the same failure to generic model_error. Verify the boundary log still exposes the diagnostic. This does not require implementing a new production flow.

### Logging and failure paths

Assert strict JSON serialization, matching report contents in logs and exceptions, stable codes, correlation IDs, and useful hints. Exercise unknown profiles, missing metadata, unsupported hooks, tokenizer failures, loader failures, and timeouts. A log-write failure must never trigger prediction after a rejection.

### Compatibility and test isolation

Keep representative valid raw-response fixtures byte-equivalent after serialization where their existing contract requires it. Preserve copy isolation, lazy imports, one load per registry configuration, retry after failed load, and model-specific limits.

Default tests remain offline and do not download weights. Supply reproducible pinned tokenizer/config fixtures and the independently pinned SDK construction implementation with manifests and applicable notices. The identical tokenizer JSON can be stored once while keeping the two tokenizer configurations separate. If fixtures are prepared rather than committed, document and execute that explicit setup before the acceptance run; missing fixtures must fail the qualification gate, never silently skip it. Ordinary test execution must not silently access the network.

### Live qualification

On the intended Mac, record installed versions, resolved model revision, tokenizer fingerprints, actual limits, and hook status. Verify a fitting prediction and that rejection occurs before request inference. Qualify the code model separately before marking it supported.

No live check is claimed complete by this design. Record pending Mac qualification explicitly in implementation results.

## 12. Sol execution contract, TDD sequence, and recovery

### Owner and scope

**Sol is the implementation owner. Astra is the recovery/technical decision agent.** Sharon will explicitly ask Sol to execute this plan later. The current PR is a separate, documentation-only PR. Do not implement the feature as part of preparing that PR, and do not merge it automatically.

When assigned implementation, Sol must read this complete plan, the research report, the plan-verification record, applicable repository instructions, and current main. Keep implementation isolated from unrelated work. By default, create a separate implementation branch/PR based on the merged plan; if the plan is unmerged, use an explicitly assigned stacked branch. Reuse the planning PR for code only if Sharon explicitly assigns that PR for implementation. This planning delivery remains documentation only. Do not attach implementation to another feature's PR.

The ordinary success contract, timeout/loader behavior, existing tests, and offline examples are protected. The already-agreed strict rejection of previously trimmed input remains intentional. Live Mac qualification is a separate recorded gate and must not be described as completed by mock or Linux tests.

### Before the first implementation change

Record the base commit, clean working-tree status, environment versions, and exact setup/test commands. Install the documented test dependencies, build the TypeScript helper, then run `npm --prefix typescript-helper test` and `python -m pytest -q` against the untouched implementation base. Capture complete output, exit codes, test counts, skips and warnings. An older planning baseline is supporting evidence, not a substitute for this fresh run.

If any baseline test fails or required check cannot run, **stop and ask Astra**. Do not change product code to hide an unexplained baseline failure. Astra must classify source/environment/fixture causes and give a concrete recovery and recheck procedure.

Create a progress/evidence log in `docs/token-budget/implementation-progress.md` before coding. Record each increment's planned behavior, files, expected new-test failure, red/green commands and outcomes, regression checks, commit SHA, and any Astra decision reference. Each published implementation commit updates this log.

### Small TDD cycle

For each increment:

1. State the one complete scenario and its dependencies.
2. Add the smallest meaningful tests for that behavior. Before running, record the exact expected failure caused by the missing capability.
3. Run the focused new test and observe that expected red result.
4. Implement only enough to satisfy the scenario.
5. Run the new tests and affected existing regression tests; inspect the diff for unrelated changes.
6. Refactor only within that green scenario, then rerun relevant checks.
7. Commit the tests, implementation, and evidence together only after the increment is green.

Expected red is restricted to a newly added test failing for its predeclared missing capability. Import/setup errors, an existing-test failure, a different failure reason, or a failed green/regression check are unexpected and require Astra. Do not publish intentionally failing intermediate commits.

“A/B” comparison here means controlled baseline-versus-new behavior, not a statistical experiment. For fitting requests, compare the independently pinned SDK's normalization/token IDs and the new inspector, and preserve the existing mocked prediction JSON/arguments. For overflowing requests, establish where the old SDK would slice, then prove the guarded path refuses with zero request inference. No production bypass switch is needed.

### Dependency-ordered implementation commits

Each numbered item is a separate green implementation commit. Do not combine broad stages into one final commit. If a listed increment cannot remain small and independently testable, ask Astra to prescribe a finer split and update this ledger first.

| Commit | Complete testable increment | Required evidence before moving on |
|---|---|---|
| 1 | JSON-safe report and typed error family; migration guidance | Serialization, immutable report snapshot, stable codes, unknown versus zero counts, message/report distinction |
| 2 | Load/use the exact pinned tokenizer and reproduce normalization | Extensive exact-ID tests for English/TypeScript, whitespace/special tokens, labels, state serialization, dict/list inputs, repeatability, and separate tokenizer configurations; no inference |
| 3 | Qualify tokenizer/assembler parity against independently pinned SDK helpers | Direct versus cached builder comparison, option order, structured criteria/custom boolean labels where accepted, special-token overhead and synchronization; qualification is mandatory before later accounting |
| 4 | Account for option caps, shared-head redistribution and instructions | Below/at/above each head-stage cut; long options with tiny total input; separate marker/text units; no misleading double-counted loss |
| 5 | Add state, full-sequence and final-slice accounting; complete all-question report | String and conversation-list direction, exact boundaries, head overflow, multi-question different allowances, all violations without partial prediction |
| 6 | Verify model/runtime profiles and classify unsupported inspection | Resolved identity, config/tokenizer fingerprints, effective limits, version/semantic mismatch; no fabricated success for unknown profiles |
| 7 | Add lazy registry/provider capability while preserving existing API behavior | Original agent identity, loader/predict arguments, optional keyword ownership checks, one lazy load, reuse, and failed-initialization retry |
| 7a | Accept verified same-directory local checkpoint identity (Astra D002) | Real path binding, canonical identity preserved, all revision/runtime/fingerprint refusals retained; focused and full Python regression |
| 8 | Wire explicit providers into existing test fixtures, offline examples and wrappers | Existing assertions and examples remain valid; no heavy SDK import or network requirement in mock runs; real wrappers forward verified capability |
| 9 | Enable shared prediction enforcement and structured logging together | Request snapshot reuse; any violation refuses before any forward; one structured boundary ERROR; matching report; loader, response-validation, timeout and logging-failure behavior preserved; cached tokenizer/method integrity before SDK validation (Astra D006) |
| 10 | Prove both block paths and a minimal flow consumer receive the same diagnostics | No block retry/enrichment/reducer on failure; unchanged fitting behavior; existing sandbox's generic result still has actionable boundary diagnostics and migration hints |
| 11 | Add controlled live qualification support and complete implementation evidence | Harness/default-off behavior tested offline; full repository regression run; actual Mac evidence recorded only if performed; code model remains unqualified until its own live checks pass |

Commits 1–8 add and verify capabilities before changing production prediction behavior. Commit 9 is the first enforcement integration and must include refusal and logging as one working scenario. Commit 10 must not introduce automatic flow recovery. Commit 11 must not relabel absent live evidence as success.

At each commit, run its focused tests plus affected existing tests. Run the full Python suite after changes to shared registry/prediction behavior, and run both full documented suites before implementation delivery. Rebuild and rerun TypeScript checks whenever its sources/build contract change. These are minimum gates; Astra can require additional targeted evidence for a discovered risk.

### Mandatory Astra recovery protocol

Trigger this protocol for **any** baseline failure, unexpected test failure, regression, new unsupported assumption, or plan mismatch, even a small one. Suspected intentional failure of an existing test still triggers it.

1. Stop the affected implementation work and preserve the working diff, failing output and reproduction.
2. Ask an **Astra** agent for a decision. Supply the plan/increment, base and current commits, exact command/output, before-versus-after evidence, affected files, and relevant model/runtime/config identity.
3. Request an explicit classification and recovery: cause, permitted edits, how to preserve the intended contract, disposition of the failed test, exact rechecks, and whether the plan needs amendment.
4. Record Astra's decision in `docs/token-budget/deviations.md`, update the plan/progress before applying any approved adjustment, and then implement the bounded correction.
5. Rerun the failed test, targeted regression checks, and broader checks Astra requires. Resume the sequence only when green and back within the documented plan.
6. If recovery needs a product/scope decision beyond the existing requirements, Astra must identify it and Sol must bring that specific decision to Sharon. If Astra cannot be reached, report the block; do not silently substitute another policy.

Astra must never be asked merely to bless deleting tests. No suite deletion, weakened assertions, blanket skip/xfail, guard bypass, silent truncation, threshold manipulation, or changed model limits to manufacture passing results. If an old assertion genuinely conflicts with strict rejection, Astra must document that specific conflict and prescribe equivalent or stronger replacement coverage. Preserve unaffected tests.

An expected focused TDD red described above is not a deviation. A plan-prescribed ordinary implementation step needs no additional approval. All other mismatches follow this protocol.

### Implementation completion

Deliver the small commit history, current plan/progress/deviation records, complete test evidence, unchanged-success comparisons, intentional overflow changes, and unresolved live qualifications. Report exact commands/counts and known limitations, not “everything works” based only on mocks.

The code-model load/encoding check and intended Mac runtime inventory remain pending until actually executed. Sol must not activate or claim an unqualified profile just to finish the plan. No product code has been changed in this planning PR.

## 13. Evidence links

- [Current flow directory](https://github.com/SharonLanger/laya-context-router/tree/83211fd88d10e4c0854797dec47df33ce8d04ea5/src/laya_context_router/flows)
- [Shared prediction boundary](https://github.com/SharonLanger/laya-context-router/blob/83211fd88d10e4c0854797dec47df33ce8d04ea5/src/laya_context_router/laya/predict.py)
- [Current RunConfig](https://github.com/SharonLanger/laya-context-router/blob/83211fd88d10e4c0854797dec47df33ce8d04ea5/src/laya_context_router/laya/config.py)
- [Prompt-submit integration](https://github.com/SharonLanger/laya-context-router/blob/83211fd88d10e4c0854797dec47df33ce8d04ea5/src/laya_context_router/hooks/user_prompt_submit/prompt_context_enrichment.py)
- [Research results and pinned SDK/checkpoint sources](https://chatgpt.com/library?file_id=libfile_23c4bc94abbc8191bd2126cd33733b7a&account_id=personal)
