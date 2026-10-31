# Sol handoff: finish first flow and retire sandbox tests

Status: handoff only. Creating this document does not implement the cleanup.
Repository: SharonLanger/laya-context-router
Work in existing draft PR #29: https://github.com/SharonLanger/laya-context-router/pull/29
Branch: `codex/first-method-context-flow`
Reviewed implementation head: `a8968d7fe3af4e8c223b48921b402408b186e339`

## 1. Current instructions take precedence

Sharon has clarified that the old flow was a sandbox. Name it accordingly and retire tests dedicated to that sandbox. Keep useful shared-hook and utility coverage, adapting it to the new production flow where necessary.

This supersedes the earlier design's prohibition on editing existing tests **only for this sandbox retirement and relevant hook-test migration**. It does not authorize unrelated changes.

The new flow is already implemented. Finish the cleanup; do not redesign or reimplement it. Reuse existing components and test helpers. Tokenizer work is being handled separately and is outside this task; do not add a tokenizer or its fixtures/tests here. We are waiting for that separate work.

Keep effort proportional: Sol owns implementation. Ask Astra only for a concrete unresolved issue requiring its judgment, not automatically for every routine change. Do not start repeated reviews or broad test loops.

Sharon asked for this file for another agent to execute. No code or tests were changed when it was created.

## 2. What already exists

- `src/laya_context_router/flows/first_method_context.py`: `handle_prompt(request, logger, *, registry=None)` adapts hook input; `run(...)` orchestrates enrichment.
- `src/laya_context_router/hooks/user_prompt_submit/dispatcher.py:_default_handler` already imports and calls the new flow's `handle_prompt`.
- Existing gateway and common dispatcher retain their validation, deadline, stdout isolation and serialization.
- `tests/first_flow/conftest.py` supplies fixed public block answers, a temporary copied project, real utility calls, and model-loading tripwires.
- `tests/first_flow/test_flow.py`, `test_formatting.py`, and `test_hook_integration.py` cover the new flow.
- Fixtures are under `tests/fixtures/first_flow_project/` and `tests/fixtures/first_flow_expected/`.

The new flow resolves one production .ts file from the explicit project root; classifies the task; selects a method; extracts its full code; lists direct called-method signatures/locations; fits output within 8,000 UTF-16 units; logs the exact enrichment; and returns the existing hook outcome. Explanation and test-generation requests qualify. Modification/nonselection requests produce no enrichment.

Historical verification:
- New suite: 122 passed.
- Untouched full baseline: 1,209 passed, 3 existing skips.
- Completed changed full run before the final blank-prompt correction: 1,275 passed, 56 failed, 3 skips.
- Targeted checks then restored two blank-prompt tests by retaining the existing `ineligible_request` reason.
- The remaining 54 classified conflicts are a historical inventory, **not a freshly rerun final-suite count**.
- Offline replay confirmed exact logged/returned context equality and zero stdout bytes on a skip.

Those checks used a reconstructed snapshot with 420 files verified against upstream Git blob hashes. Use a normal checkout for the final verification; do not publish a synthetic local baseline. Earlier local working-tree modifications may already be present in the remote PR, so compare with the remote head before committing anything.

## 3. Why old tests fail

The previous default hook called the sandbox. Existing tests often:
- Mock only the old method-selection SDK request; our flow first calls the requested-action block.
- Expect the old collector's supporting dependency bodies and old output wording.
- Expect warning-only handling of oversized output, whereas the new flow enforces its hard cap.
- Expect the old prompt-prefix eligibility rules or diagnostic reasons.

Do not make production behavior imitate the sandbox merely to satisfy those expectations. Do not delete a shared infrastructure test simply because its old fixture/mock happens to invoke the sandbox.

## 4. Rename and isolate the sandbox

1. Move the old orchestration implementation from `flows/file_method_context.py` to `flows/sandbox_file_method_context.py` beneath `src/laya_context_router/`. Clearly identify its module documentation and flow-specific log identity as sandbox.
2. Existing experiment/example/live-check callers import `flows.file_method_context.run`. Preserve that import with a minimal compatibility re-export of `run` from the sandbox module. Preserve its callable signature and behavior. Do not add a new registry, mode flag, selection framework, or production fallback.
3. Leave experiments and their runners unchanged. Known consumers include:
   - `experiments/flow_method_context.py`
   - `experiments/flow_missing_file.py`
   - `examples/file_method_context.py`
   - `src/laya_context_router/live_check.py`
   Recheck references before renaming; this list is a starting point.
4. The production event dispatcher must keep calling only `first_method_context.handle_prompt`. It already does; do not add another routing layer.
5. **Do not delete the old hook adapter file wholesale.** The new flow imports `_prepare_feature_config` from `hooks/user_prompt_submit/prompt_context_enrichment.py`. Keep that reused preparation helper intact. Clearly label any retained legacy `enrich_prompt_context` handler as sandbox-only; it must stay disconnected from the default route.
6. Existing shared contract/lifecycle identifiers such as `feature_id='prompt_context_enrichment'` are not proof that the sandbox is still wired in. Avoid unrelated shared-ID renames.

Do not add an automated suite to certify the retired sandbox. A read-only reference audit is enough to identify the compatibility import surface; no model or experiment execution is needed.

## 5. Test disposition

Classify tests by responsibility, including currently passing sandbox tests. Do not treat the list of 54 failures as the entire cleanup.

| Test responsibility | Action |
|---|---|
| Dedicated to old sandbox orchestration, old selection fallback, old prompt syntax or old dependency-body output | Remove from the maintained test suite |
| Gateway/event validation, stdout isolation, deadline behavior, logging or serialization | Preserve the assertion; migrate its setup to invoke the new flow with mocked public block answers |
| Actual reusable block, resolver, parser, extractor, navigation or shared formatting utility behavior | Keep component coverage |
| Shared setup helper such as explicit project-root/config preparation | Keep coverage, including helpers still used by the new flow |
| Duplicate of an adequate existing `tests/first_flow/` case | Remove the obsolete sandbox-specific duplicate and note the retained replacement case |

Historical failing files and case counts:

| File | Count | Required review |
|---|---:|---|
| `tests/test_hook_scenarios.py` | 14 | Preserve useful hook scenarios; replace old flow-specific mocks/oracles |
| `tests/test_prompt_hook.py` | 21 | Split useful gateway guarantees from sandbox formatting/eligibility assumptions |
| `tests/test_project_root_hook_mode.py` | 7 | Preserve root-only lookup guarantees; retire direct sandbox-only checks |
| `tests/test_dependency_flow.py` | 3 | Retire sandbox orchestration/body expectations; preserve any independent utility coverage |
| `tests/test_gateway_migration_baseline.py` | 2 | Replace/remove obsolete old-flow comparison assumptions; retain actual gateway guarantees |
| `tests/test_project_flow.py` | 6 | Retire old collector-flow expectations; preserve independent shared utility coverage |
| `tests/test_prompt_context_preparation.py` | 1 | Preserve reused preparation-helper tests; adapt obsolete default-route expectations |

Also inspect direct sandbox users, including:
`test_file_method_context.py`, `test_file_method_context_deferred.py`,
`test_flow_branches.py`, `test_method_ambiguity_fallback.py`,
`test_prompt_file_list.py`, and `test_v2_flow_composition.py`.

These are review targets, not blanket file-deletion instructions. Mixed modules can contain useful component tests. Some tests import setup helpers from `test_file_method_context.py` or `test_prompt_hook.py`; trace those imports before removal. Reuse existing new-flow helpers, or move only the still-needed small helper to test support. Avoid leaving broken imports or creating a new mocking framework.

Record a compact removed/adapted/retained summary in the PR description. Do not create a large evidence tree. Do not use skips, xfails, pytest exclusions, or weakened assertions to conceal obsolete tests.

## 6. Flow tests: mock building blocks

Reuse the existing new-flow harness. Replace these public calls:
- `building_blocks.questions.requested_action.block.run`
- `building_blocks.questions.method_selection_v2.block.run`

Supply fixed valid `BlockResult` answers. Verify orchestration:
- explain/generate_tests -> selection -> extraction/navigation -> context.
- modify_code/undecided -> no enrichment.
- selection chooses X -> extract exactly X using its opaque ID.
- no selection -> no extraction or enrichment.
- complete method too large -> no enrichment.
- navigation rows exceed remaining space -> retain fitting whole entries and correct omission note.

Run deterministic TypeScript utilities against the copied test fixture. Do not invoke LAYA reasoning, a model loader, real tokenizer, or network inference. Keep tripwires. Only inject utility failures for explicit error-path cases; normal success uses the real utilities.

For hook integration, use the real gateway and both dispatchers, replacing the public block calls. Preserve:
- source/config resolution from explicit project root despite another cwd;
- exact source formatting and line ranges;
- full selected method, direct call list only, bounded final text;
- exact equality between decoded logged enrichment and returned additionalContext;
- one valid hook JSON object on success;
- zero stdout bytes on no enrichment, including errors;
- existing stdout-noise isolation and deadline handling.

Do not retest internals of already-tested building blocks inside the flow suite.

## 7. Execution order and checks

1. Fetch the current PR branch and base in a normal checkout. Check repository instructions and preserve unrelated work. Sharon mentioned preceding PR work: check whether it landed before updating this branch; do not merge another PR or start tokenizer integration yourself.
2. Inspect imports/test responsibilities. Prepare the small retirement/migration list.
3. Rename the sandbox and keep the necessary compatibility entry. Preserve the already-correct new dispatcher route.
4. Retire sandbox-only tests; adapt useful shared-hook tests using existing block mocks. Keep production implementation changes limited to actual defects found.
5. Run the relevant focused groups while editing. After cleanup, run the new-flow suite and **one** full Python suite. Repeat a failing focused group after a correction; do not repeatedly rerun the entire suite without a concrete reason.
6. Audit the diff and update the PR description/design notes to reflect the final scope and actual test results. Remove stale instructions that prohibit this now-authorized test cleanup or mandate automatic repeated Astra review.
7. Report completion and remaining issues to Sharon. Leave PR #29 unmerged.

Existing setup commands, if dependencies/build are absent:

```bash
python -m pip install -e '.[test]'
npm --prefix typescript-helper ci
npm --prefix typescript-helper run build
```

Validation:

```bash
python -m pytest -q tests/first_flow
python -m pytest -q
```

Use the existing test setup, dependencies and scripts. Do not change package/lock files to perform this cleanup. Do not run live model checks, experiments, or a real tokenizer. Preserve and report pre-existing skips separately.

## 8. Completion criteria

- Old flow clearly identified as sandbox; no sandbox-only automated tests remain.
- Existing experiment imports continue to resolve through the compatibility entry.
- Default hook route calls only the new flow.
- Shared hook guarantees and reusable utilities retain meaningful coverage.
- New flow tests use fixed building-block answers; deterministic utilities run normally.
- Relevant tests pass; remaining failures are investigated and reported rather than hidden.
- No experiment, shared model/runtime, tokenizer, utility implementation or unrelated refactor changes.
- The PR contains a short cleanup summary and actual test results.
- Tokenizer is documented as separate pending work, not implemented here.
- No merge or deployment is performed.

If a genuine new shared-component defect prevents completion, describe the specific issue and smallest proposed change before expanding scope. Routine sandbox-test retirement and relevant hook-test migration are already authorized by Sharon.
