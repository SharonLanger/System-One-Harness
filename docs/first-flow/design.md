# LAYA first method-context flow — design and Sol handoff

Date: 2026-10-31  
Status: implementation authorized; draft PR work may proceed while tokenizer support is pending.  
Companion: [Detailed test cases](https://chatgpt.com/library?file_id=libfile_faf266273578819184fa45bb06283809&account_id=personal).

This revision supersedes the earlier first-flow design and test plan wherever they proposed broader changes. Sharon's boundary is binding: **add the flow, register it with the existing dispatcher, and add focused tests. Reuse everything else.**

Latest decision: tokenizer readiness does not block implementing or testing this flow or preparing its dispatcher connection in a draft PR. **Tokenizer support must be added and validated before this PR is merged.** Keep the PR unmerged; list the outstanding integration and tests explicitly. Do not implement shared tokenizer support as part of this flow task.

## 1. Change boundary

| Allowed implementation change | Exact location |
|---|---|
| One new flow module, including its small hook adapter and private formatting helpers | `src/laya_context_router/flows/first_method_context.py` |
| Minimal import/call change to connect the flow | `src/laya_context_router/hooks/user_prompt_submit/dispatcher.py:_default_handler` |
| New tests and test-local support | `tests/first_flow/` |
| A copied project fixture and new flow-specific expected-output fixtures | `tests/fixtures/first_flow_project/`, `tests/fixtures/first_flow_expected/` |
| This handoff and its companion test plan in the PR | `docs/first-flow/design.md`, `docs/first-flow/test-plan.md` |

Do not modify experiments, experiment tests/runners, examples, existing building blocks, questions, rules, TypeScript utilities, the old flow, the old enrichment handler, shared model/tokenizer runtime, logging infrastructure, gateway, common dispatcher, plugin configuration, dependency files, build scripts, or unrelated tests.

Existing tests remain unchanged under this plan. Run relevant existing tests as regression checks; a failure does not authorize rewriting them. Section 11 identifies the known default-route compatibility issue.

No separate contracts package, generic formatter framework, budget observer, registry extension, payload-file writer, new CLI flag, legacy-mode launcher, evidence-log tree, or broad refactor is needed. Small helpers belong to the new flow module. Test support stays in the new test directory. Do not create log files in the tracked change set.

## 2. Behavior

For a prompt referring to one production TypeScript file:

1. Resolve the file using the explicit project root.
2. Ask the existing requested-action building block what the user wants.
3. For explanation or test generation, obtain the file's callable outline and ask the existing selection building block which method is relevant.
4. Extract that method's complete implementation using its selected identity.
5. Obtain one level of outgoing method locations.
6. Return bounded additional context containing the implementation and navigation list.

Treat building-block answers as definitive. Do not reclassify their answers, inspect confidence to make another decision, tune rules, retry, or call a replacement model. Production-code modification requests receive no enrichment in this first flow.

The first implementation is sequential. The user's suggestion to parallelize is optional; concurrent inference and cancellation machinery are outside this first-flow scope.

Only the selected implementation is included. Called methods contribute root-relative path, signature, and inclusive definition-line range. Do not collect their bodies, transitive dependencies, incoming callers, unrelated declarations, or extra imports.

## 3. Invocation and system connection

The existing command already invokes the hook:

```text
"${LAYA_CONTEXT_ROUTER_CLI}" hook --hook UserPromptSubmit --repository-root "${CLAUDE_PROJECT_DIR}" --real
```

The call chain remains:

1. `hooks/gateway.py:main` — input, stdout isolation, deadline, serialization.
2. `hooks/dispatcher.py:dispatch_hook` — common validation and event routing.
3. `hooks/user_prompt_submit/dispatcher.py:dispatch_user_prompt_submit` — prompt validation and one feature invocation.
4. `_default_handler` — the sole existing production function edited for this flow.
5. New `flows/first_method_context.py:handle_prompt`, then `run`.

All abbreviated source paths above are under `src/laya_context_router/`.

The intended dispatcher edit is limited to:

```python
def _default_handler(request, logger):
    from ...flows.first_method_context import handle_prompt
    return handle_prompt(request, logger)
```

Preserve the existing handler-injection seam, dispatcher validation, lifecycle logs, and public feature ID. New flow logs may add `flow_id="first_method_context"`. No change to the common dispatcher or gateway is needed.

Proposed callable surface in the new module:

```python
handle_prompt(request, logger, *, registry=None)

run(prompt, *, project_root, config, registry, logger,
    max_context_chars=8000)
```

`handle_prompt` adapts the existing `PromptRequest`, reuses configuration preparation, and creates the existing registry only when one was not supplied. `run` owns orchestration and returns the existing `Context`, `Noop`, or `Failure` contract directly. No new public result schema is introduced.

Resolve block functions at call time so tests can replace their public call boundaries. Do not bind real model functions as default arguments. The registry is invocation-scoped; do not add shared mutable state.

## 4. Existing components to call

| Step | Existing component | Input and use |
|---|---|---|
| Hook setup | `hooks/user_prompt_submit/prompt_context_enrichment.py:_prepare_feature_config` | Reuse root validation, real-mode opt-in, config loading; leave that file unchanged |
| Registry | `laya.registry.AgentRegistry` | Existing constructor and behavior only |
| Find references | `building_blocks.file_reference_utils.detect_configured_references` | Original prompt; configured TypeScript detector |
| Resolve reference | `building_blocks.resolve_file.resolve_file` | Explicit root mode; no cwd fallback |
| Determine task | `building_blocks.questions.requested_action.block.run` | `{"prompt": prompt}`, existing config and registry |
| List methods | `building_blocks.typescript.outline` | Canonical absolute selected file |
| Select method | `building_blocks.questions.method_selection_v2.block.run` | `{"text": prompt, "source_outline": outline_result}`, existing config and registry |
| Read method | `building_blocks.typescript.extract_callable` | Absolute file and selected opaque ID |
| Find called methods | `building_blocks.typescript.get_called_method_locations` | Root-relative selected file, selected ID, explicit project root |
| Check selected snapshot | `building_blocks.typescript.outline` | Repeat after navigation; compare source hash |
| Return hook result | `hooks.contracts.Context/Noop/Failure` | Existing result types |
| Log | Logger supplied by gateway; existing `log_utils` underneath | Small flow events and one exact final enrichment field |
| Serialize | Existing gateway `serialize_response` | No serialization in the flow |

The configuration helper is private but already implements the needed behavior. Reuse it without moving it, renaming it, or extracting a new shared helper. If repository policy or a later API prevents that reuse, escalate to Astra instead of refactoring.

The new presentation differs from the old dependency-collector format. Compose that text locally in the flow; do not call the old collector merely to satisfy its formatter's schema. Local formatting is part of this flow, not permission to rewrite shared formatting utilities.

## 5. Project-root-only reads

Require an absolute, existing project directory supplied by `repository_root`; canonicalize it. Missing, relative, nonexistent, or non-directory roots produce `Failure`. Neither the event cwd nor process cwd is a fallback. Derived hook metadata does not override the configured root.

Call the resolver as:

```python
resolve_file(reference, cwd=project_root,
             repository_root=project_root,
             resolve_from_project_root=True)
```

Use canonical absolute source paths for outline/extraction and root-relative paths plus the explicit root for navigation. The selected file and returned navigation targets must remain inside the canonical project root, including through symlinks. Render forward-slash paths relative to that root.

Relative optional configuration-file paths must also be rooted explicitly. In the new adapter only, make a shallow copy of request/config arguments and replace a relative config path with the explicit-root-based absolute path before calling the existing preparation helper. Do not mutate the incoming request or change `load_config`. Invalid roots must fail before any config read. Explicit absolute config paths remain explicit resources.

Installed helper/model resources retain their existing installation-relative lookup; they are not searched for inside the analyzed project.

Production eligibility for this first version is `.ts`, excluding `.spec.ts`, `.test.ts`, and `.d.ts`. Check both the mentioned filename and the canonical target. Reuse the detector with an include pattern for complete `.ts` names and no exclusions so test/declaration mentions are visible to the flow's explicit gate. Do not add recognition logic for unsupported extensions.

## 6. Orchestration and outcomes

1. Validate setup and prompt. An empty prompt yields `Noop`.
2. Detect references. Deduplicate identical spellings; resolve each from the root. Deduplicate successful resolutions by canonical file identity.
3. Require exactly one eligible file. No reference, missing/ambiguous target, or multiple distinct recognized TypeScript files yields no context. Do not discard an unresolved second reference to keep a convenient first one.
4. Call requested-action once with the unmodified prompt. `explain` and `generate_tests` continue. `modify_code`, `undecided`, and explicit block skips stop.
5. Obtain the real outline. Empty candidates stop.
6. Call method selection once with the original prompt and complete outline. An explicit skip or no selected ID stops. Use the accepted opaque ID, never reselect by method name.
7. Extract the exact implementation. The extraction must match the selected file, identity, and outline hash. The utility already validates its transport schema; do not duplicate its parser/validator.
8. If the mandatory method text and fixed presentation already exceed the output budget, stop before navigation. Never shorten the method.
9. Call outgoing navigation once. Preserve its order and deduplicate repeated target identities; never recurse. Retain usable partial results with the fixed partial note. An ordinary navigation error permits method-only context with the fixed unavailable note.
10. Recheck the selected source hash through the existing outline utility. A changed, missing, or invalid selected source stops enrichment. Do not retry against a fresh selection.
11. Render and pack complete navigation rows within the final budget. Log the exact final text and return `Context(text)`.

Malformed block transport/identity is a failure; validating identity is not reevaluating a block's answer. Preserve accepted skip reasons in diagnostics. Unknown internal details never become hook prose.

Selected-source errors, configuration errors, and block exceptions produce `Failure`; deliberate nonselection and size refusals produce `Noop`. Both serialize to no enrichment. Do not fall back to the old flow.

Allow the gateway's `TimeoutError` to propagate; never convert it into successful partial context. The current utility may wrap its subprocess timeout as `TypeScriptError`; preserve that existing API behavior. Do not change utility exception types or parse exception prose to redesign timeout handling. The gateway still owns the overall deadline.

The final hash check protects the selected snapshot during assembly. It does not establish an atomic snapshot of every called file or prove runtime dispatch.

## 7. Exact additional-context format

Use the following layout. Fences here illustrate the payload; do not include them in the actual string.

```text
Enriched Prompt for System 1
File: src/billing/invoice-service.ts | Method: calculateInvoiceTotalWithAdjustment | Lines: 21–24
export function calculateInvoiceTotalWithAdjustment(invoice: Invoice, adjustment: number): number {
  const base = calculateInvoiceTotal(invoice);
  return roundToCents(base + adjustment);
}

Methods called by calculateInvoiceTotalWithAdjustment:
src/billing/invoice-service.ts | export function calculateInvoiceTotal(invoice: Invoice): number | Lines: 6–19
src/utils/rounding.ts | export function roundToCents(value: number): number | Lines: 1–3

Context scope: selected method only.
```

Implementation starts immediately below the method metadata. Preserve the extracted `code` string exactly: indentation, tabs, comments, Unicode, and original line endings. Do not use prettified `display_code`, line prefixes, Markdown fences, or a dedented/trimmed copy. Add section separators outside the source string.

Definition lines are inclusive. The selected first line comes from the utility's location; determine the last line from the exact extracted text using the existing formatter's line-break semantics: CRLF is one break; CR, LF, U+2028 and U+2029 are breaks; a trailing terminator does not invent another definition line. This small calculation belongs to presentation, not source parsing. Outgoing definition ranges come directly from navigation, not call-site ranges or opaque-ID offsets.

Each outgoing entry is one metadata line. If a signature contains line breaks/control characters, escape those visibly in metadata only; do not normalize or rewrite the implementation.

Use only these necessary coverage notes:

| Situation | Text |
|---|---|
| Successful navigation with no reported methods | `No project methods were reported.` |
| Partial navigation | `Call list is partial; some targets could not be resolved.` |
| Navigation unavailable | `Call list unavailable.` |
| Known returned entries omitted for size | `<N> additional reported methods omitted to fit the context budget.` |

Partial status and budget omission may both be present. Omitted counts concern known returned entries only. No debug dictionaries, confidence, token reports, error tracebacks, success banners, or no-op messages belong in the context.

## 8. Output budget and hook protocol

The application limit is 8,000 UTF-16 code units. Use the existing `max_context_chars` argument to lower it; a larger setting cannot raise the first-flow cap. This is an application policy, not a claim about Claude's universal limit.

Count the entire final additional-context string: title, metadata, implementation, separators, call rows, notes, and footer. Use `len(text.encode("utf-16-le")) // 2`. Invalid Unicode produces a formatting failure.

Keep the complete implementation. For N navigation entries, consider complete prefixes of length 0 through N, including each prefix's correct omission/status notes, and select the largest fitting prefix. Do not cut rows, paths, signatures, or source. Do not reject solely because the zero-row candidate is too large: the full list may be shorter than a long omission notice. If no valid representation fits, return `Noop(output_budget_exceeded)`.

The existing gateway alone emits:

```json
{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"<final text>"}}
```

On a skip or failure, stdout must contain **zero bytes**, not `{}`, a reason string, or an empty-context envelope. Existing stderr/log diagnostics are permitted. Do not introduce a second wire property, change the original user prompt, print from the flow, or bypass gateway isolation.

## 9. Tokenizer handling: reuse only

LAYA input tokens and Claude context characters are separate limits. Output fitting does not prove that a LAYA request fits.

The existing shared model boundary must perform its own exact pre-inference inspection, including generated questions and choices. The flow consumes its existing result/error/report interface. It does not tokenize a second time, estimate tokens from characters, modify the registry, add an observer, change block return types, or bypass the guard.

For each block invocation:

- If the existing block API returns token metadata, retain it in diagnostics attributed to that block. Use its actual public field; do not invent a field or extend `BlockResult`.
- If no metadata is exposed, record unavailable, not zero or “fits.” A definitive semantic answer remains definitive.
- Preserve preflight required/retained/limit counts separately from post-inference usage. Do not sum unrelated sequence counts to evaluate one sequence's limit.
- A typed oversize refusal stops this flow without retry: `Noop(input_token_budget_exceeded)`.
- Typed inspection-unavailable/inspection-failed outcomes stop with `Failure` at the active block stage.
- Other block errors stop with `Failure(block_error)`. Timeout retains gateway behavior.

No truncating prompts, candidate lists, model switches, raised limits, or old-flow fallback after a refusal.

**Observed dependency:** the inspected main prediction boundary still calls `agent.predict` directly and does not enforce the proposed guard. The inspected `BlockResult` contract does not establish a universal success-token field. Tokenizer work discussed as PR #23 must be verified on the actual implementation base; this document does not declare it complete.

Sol can build/test the flow and prepare the dispatcher connection in a draft PR while that dependency is unresolved. Sharon explicitly authorized proceeding now. Do not block that work on the missing guard or add an activation flag. Before merge, integrate and verify the existing guard and its real public error/report surface, then complete the dependent flow tests. Implementing the shared guard or adding success-report plumbing belongs to its separately authorized task. Do not fabricate a parallel production API to make tests pass.

The PR description must retain this unchecked merge gate until verified:

- [ ] Add/integrate tokenizer support before merge: inspect the full prepared LAYA request before inference, consume the established token/error surface at both block boundaries, and complete dependent flow tests with mocked tokenizer/block outcomes. No unit test may call a real tokenizer or model.

## 10. Logging

Reuse the supplied logger and current JSONL format. Add compact stage/outcome information and one `enrichment_prepared` event containing the final string as `additional_context`, plus flow ID, relative method identity, UTF-16 size, and included/omitted row counts. Existing gateway correlation supplies invocation/session IDs.

The logged field must equal `Context.text` exactly. JSON escaping on disk is normal: decoding the log record must recover the exact code and line endings. Do not prettify, dedent, split into line records, or independently regenerate a “log version” of the text.

Log this full final enrichment once per successful preparation; skip/failure paths have no payload event. Token metadata belongs only in compact diagnostic fields. Do not add a separate plaintext artifact writer, log directory, global log settings, or new logging service. Existing utility logging stays unchanged.

Ordinary logging failure is best-effort and must not contaminate stdout or alter a valid context. Timeout still propagates. “Prepared” means assembled, not delivered; rely on existing gateway completion records for emission status.

## 11. Tests, fixtures, and known compatibility issue

Implement the 61 detailed cases in the companion plan, using parameterization where useful. These are flow tests: mock both LAYA building blocks at their public call boundaries. Run the existing deterministic detector, resolver, TypeScript outline/extractor/navigation utilities, formatter logic, dispatchers, and serializer at the appropriate test level.

Copy `experiments/fixtures/connected_project/` once to `tests/fixtures/first_flow_project/`, preserving its source tree, imports, and tsconfig. Do not edit the original or execute experiment runners. Record the origin path/commit in the copied fixture's README. Each test operates on a temporary copy. Add small synthetic edge fixtures only within the new test area.

Install loader/prediction tripwires so this suite cannot run a real model, fetch weights, or use network inference. Missing Node/helper builds are setup failures, not a reason to mock the utility or silently skip coverage.

**Known compatibility issue:** `tests/test_hook_scenarios.py` and its shared old hook expectations include exact old enrichment output and SDK-level mocks for the old route. Switching the default flow changes those assumptions. The new suite must test the actual default route with both blocks mocked, but it must not secretly replace, bypass, or rewrite the existing suite.

Before landing the dispatcher switch, Sol must reproduce the affected baseline/changed expectations and send the narrow conflict to Astra. Astra must propose the smallest resolution; if it requires existing-test edits outside this allowlist, Sharon must authorize that scope change. Do not claim all regressions pass while excluding these tests. Keep the dispatcher change unlanded until this is resolved. No additional production compatibility mode is authorized.

## 12. Sol's implementation instructions

Sharon has authorized implementation and a draft PR. Merge remains unauthorized and blocked on tokenizer support.

1. Read repository instructions, record the base revision, and inspect existing relevant tests before editing. Establish baseline results and isolate unrelated working-tree changes.
2. Add only the copied test fixtures and new test-local support. Confirm no experiment file changes.
3. Implement the new flow incrementally: root/action gates, selection/extraction/navigation, formatting/budget, token-outcome consumption, logging, adapter. Add focused tests for each.
4. Record the deferred tokenizer integration as a required pre-merge PR checklist item and resolve the documented old-default-test conflict through Astra. Do not expand scope to fix either.
5. Apply the minimal dispatcher connection under Astra's scoped integration decision; the missing tokenizer guard does not block preparing that change in the draft PR. Test the real default chain with mocked blocks.
6. Run focused and affected regressions, review every changed path against section 1, and report results and any unresolved dependency truthfully.

Use the repository's documented setup. On the reviewed base the normal prerequisites/checks are:

```bash
python -m pip install -e '.[test]'
npm --prefix typescript-helper ci
npm --prefix typescript-helper run build
python -m pytest -q tests/first_flow
python -m pytest -q tests/test_hook_common_dispatch.py tests/test_user_prompt_dispatch.py tests/test_hook_gateway_transport.py tests/test_hook_deadline_lifecycle.py tests/test_hook_scenarios.py tests/test_prompt_hook.py tests/test_project_root_hook_mode.py
python -m pytest -q
```

Run these in the repository root, not the target project's cwd. Use existing test/build dependencies; do not change package/lock files. Keep tests and artifacts in temporary directories. Existing utility tests may be run unchanged when relevant; do not add a utility or model test project for this flow.

Record a compact implementation summary with test commands/results and decisions. No large generated progress/evidence trees are required. No merge, deployment, plugin installation, or unrelated cleanup is authorized by this document.

## 13. Mandatory Astra escalation

**For any deviation from this plan, Sol must stop the affected work and spin off Astra before deciding or applying a workaround.** Expected red failures from newly added feature tests are not deviations; unexpected failures, API mismatches, dependency gaps, behavior changes, and files outside the allowlist are.

Use the Astra model (`gpt-6-astra`) when model selection is supported. Send:

- Design section and test IDs.
- Base/current revision and relevant diff.
- Expected behavior versus actual behavior.
- Exact reproducer and failure output.
- Proposed smallest options, including any additional file changes.

Ask Astra to decide the technical recovery and required checks. Astra may resolve technical choices within the approved scope; only Sharon can authorize expanding that scope. If Astra is unavailable, report the blocked work and preserve it. Do not substitute Sol's own decision.

Never delete tests, weaken assertions, add blanket skips/xfails, hide failures, change block rules, introduce fallback behavior, or modify experiments to obtain green tests. Resume the affected work only after the decision is recorded and the plan is consistent with it.

## 14. Acceptance and remaining decisions

Acceptance requires:

- Only allowlisted changes, with original experiments and shared components untouched.
- Mocked block decisions and real deterministic utility coverage.
- Root-only source reads and source fidelity.
- Full selected method plus direct called-method locations within the cap.
- Exact enrichment/log agreement and clean hook stdout.
- Relevant regressions passing without hidden exclusions.
- Existing tokenizer protection integrated and verified before merge; its absence does not block draft implementation work.

Two merge requirements remain: tokenizer support and resolution of any old-hook expectation conflicts. Tokenizer support is explicitly deferred while draft implementation proceeds. Neither requirement authorizes unrelated changes or a merge.

## 15. Source basis

Repository: [SharonLanger/laya-context-router](https://github.com/SharonLanger/laya-context-router).  
Reviewed main at this revision: `223b83b90c7c8f3b397c17f80f48908b579a8556`. No repository files were changed while preparing this design.

- [Event dispatcher](https://github.com/SharonLanger/laya-context-router/blob/223b83b90c7c8f3b397c17f80f48908b579a8556/src/laya_context_router/hooks/user_prompt_submit/dispatcher.py)
- [Existing setup helper](https://github.com/SharonLanger/laya-context-router/blob/223b83b90c7c8f3b397c17f80f48908b579a8556/src/laya_context_router/hooks/user_prompt_submit/prompt_context_enrichment.py)
- [Requested-action block](https://github.com/SharonLanger/laya-context-router/blob/223b83b90c7c8f3b397c17f80f48908b579a8556/src/laya_context_router/building_blocks/questions/requested_action/block.py)
- [Method-selection block](https://github.com/SharonLanger/laya-context-router/blob/223b83b90c7c8f3b397c17f80f48908b579a8556/src/laya_context_router/building_blocks/questions/method_selection_v2/block.py)
- [Existing TypeScript bridge](https://github.com/SharonLanger/laya-context-router/blob/223b83b90c7c8f3b397c17f80f48908b579a8556/src/laya_context_router/building_blocks/typescript.py)
- [Inspected prediction boundary](https://github.com/SharonLanger/laya-context-router/blob/223b83b90c7c8f3b397c17f80f48908b579a8556/src/laya_context_router/laya/predict.py)
- [Existing hook expectations](https://github.com/SharonLanger/laya-context-router/blob/223b83b90c7c8f3b397c17f80f48908b579a8556/tests/test_hook_scenarios.py)

