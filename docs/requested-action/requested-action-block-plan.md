# Implementation authorization update

Sharon authorized implementation on 2026-10-31 in the same PR #19 and chose to
retain this plan. Those instructions supersede the separate-PR/removal directions
below. The original plan is retained as the implementation specification. See
[verification evidence](verification.md) for execution results and Astra decisions.

# Requested-action building block — implementation and test plan

Status: PLAN ONLY. No implementation, test execution, commit, or PR publication
is performed by creating this document. Implementation requires Sharon's go-ahead.
Date: 2026-10-31.
Repository: https://github.com/SharonLanger/laya-context-router
Reviewed main: `6de4c8eb9691b0594b12bf5cbf2fa67c862b59ad`.
Implementation owner: Sol. Reasoning/deviation reviewer: Astra.
Standalone handoff: the implementation agent may receive only this PR URL.
The token-budget handoff is separate; section 9 contains everything necessary
for this implementation and does not require access to another file.

## Start here: instructions for Sol receiving only the PR

1. Open this PR, read its description and this entire plan from the PR head.
   Do not rely on chat history or assume this file already exists on main.
2. When Sharon tells you to implement this PR's plan, that message authorizes
   implementation. The current plan publication alone does not start the work.
3. Fetch fresh main, inspect applicable AGENTS.md, and implement on an isolated
   branch with a separate implementation PR. Keep this documentation-only PR
   unmerged. Preserve concurrent changes from other agents.
4. Execute the phases and tests below. Call Astra on any deviation as specified
   in section 11. Use an independent verifier before declaring completion.
5. Before finishing the implementation PR, ensure this temporary plan is NOT in
   its final tree. If copied/cherry-picked onto that branch, delete only this
   plan file after verification and commit its removal. Keep the permanent block
   README, tests and necessary product documentation.
6. Put execution evidence and the test-ID mapping in the implementation PR
   description (or an attached report), not a permanent copy of this plan.
7. Before an authorized merge, verify the final diff contains no temporary plan
   or duplicate of it. Merge only when Sharon authorizes it. After the completed
   implementation is merged, close this plan PR as superseded.

Deleting the plan from the final tree keeps it out of main's current files.
It does not erase PR discussion or historical commits from GitHub; no history
rewriting is requested. If a future agent cannot access this PR, ask for access
rather than reconstructing missing requirements.

## 1. Purpose and agreed scope

Given one user prompt, classify requested work into exactly one of:

- `explain`: understand production or test code without changing it.
- `generate_tests`: create additional tests using existing code as reference.
- `modify_code`: fix, refactor, or implement production or test code.

The existing rule may reject the model answer, yielding `undecided`. That is an
extraction outcome, not a fourth model criterion. No multi-label output, no second
question, no extra inference to repair an uncertain answer.

The purpose is a reusable building block that later flows can invoke. No existing
flow or hook will start using it automatically. This work does not read files,
resolve paths, run TypeScript, inspect methods, edit code, or authorize changes.

Sharon deliberately deferred resolving the overlap between test generation and
general code modification. Keep the three choices and expose that ambiguity in
evaluation cases. Do not silently add categories or a production-edit boolean.
In particular, `modify_code` does not prove production code is an editing target.
`explain` and `generate_tests` may later share a routing branch, but preserve their
distinct answers here.

Block 2 is excluded. Record only the accepted future wording for continuity:
“Does answering this request require understanding the method itself, what it
calls, how it is used, or both?” Future descriptions must make clear that relation
context includes the selected method too. Do not design or implement block 2,
depth scores, multiple-answer rules, or context assembly in this task.

## 2. Source basis and current architecture

Copilot documentation describes separate explain, tests and fix commands:
https://learn.microsoft.com/en-us/visualstudio/ide/copilot-chat-context?view=vs-2022
https://github.com/MicrosoftDocs/visualstudio-docs/blob/main/docs/ide/copilot-chat-context.md
These are task vocabulary examples, not evidence of an automatic prompt classifier
or proof of Laya accuracy. Our question and policy require evaluation.

Inspected at the baseline above:

- `src/laya_context_router/block_runtime/runtime.py` and `contracts.py`:
  composition-based Block, PreparedInput and BlockResult; copied inputs; one
  predict call; validation; one enrichment per answer; typed rule; extraction.
- `block_runtime/README.md`: complete question overrides and named rule overrides.
- `building_blocks/questions/ticket_triage_v2/block.py` and `block.json`:
  a small adapter pattern with explicit config/registry and injected catalog.
- `defaults/questions/department.json`: reusable named choice question format.
- `defaults/rules/method_selection_default.json`: existing example of ANDed
  answer_confidence >= 0.5 and probability_gap >= 0.15.
- `laya/predict.py`: validates selected labels/probability maps and preserves SDK
  errors; default checkpoint is the typed-decisions MLX model.
- `laya/registry.py`: cache key is model, temperature, language; registry lifetime
  belongs to the invocation; failed loads are not cached.
- `pyproject.toml`: wildcard packaging includes question/rule JSON and block MD/JSON.

Relevant existing tests: `tests/block_runtime/test_runtime.py`,
`tests/block_runtime/test_wheel.py`, `tests/test_packaged_blocks.py`,
`tests/test_v2_blocks.py`, and `tests/test_v2_flow_composition.py`.
No AGENTS.md appeared in the inspected remote tree. Recheck current main and any
applicable workspace instructions before implementation; other agents are active.

## 3. Proposed contract

Public Python entry point (proposed new module):

```python
from laya_context_router.building_blocks.questions.requested_action.block import run

result = run(
    {"prompt": "Write tests for calculateTotal in invoice.ts."},
    config=config,
    registry=registry,
    # Optional, matching the existing Block API:
    # rule_overrides={"requested_action": "another_choice_rule"},
    # question_overrides={"requested_action": full_question_definition},
    # prepare_input=custom_preparer,
    # catalog=custom_catalog,
)
```

### Input and preparation

Require a dict with exactly one key, `prompt`, containing a nonblank string.
Reject missing/null/nonstring/whitespace-only prompts with BlockInputError before
model loading. Detect blankness using strip, but preserve the original nonblank
string, including whitespace and Unicode, when submitting it. Reject unknown
keys so supplied code/context is not silently ignored. This is a new block's
contract; do not tighten existing blocks' validation.

Default preparation: PreparedInput(original_prompt, resolved_questions, {}).
No file or signature inputs in version 1. File names inside the prompt are text
only and must not trigger filesystem lookup. No normalization, prompt rewriting,
regex intent shortcut, conversation loading or code fetching.

Support existing per-call custom preparation, but validate its domain contract:
one local question named requested_action, type choice, and precisely the three
stable criterion IDs. Custom text may differ by explicit caller choice and must
remain a nonblank string. Do not require custom text to equal the original prompt.
The reducer must not depend on custom state. Unknown custom criterion IDs must
fail before the model runs. The generic runtime already checks names and types;
add only the block-specific checks through validate_prepared.

Question overrides can change instructions/descriptions or use a catalog ref,
but cannot change the type or stable criterion set. Pass named rule overrides
through unchanged; do not add inline policy/deep-merge machinery.

### Question definition

Proposed `defaults/questions/requested_action.json`:

```json
{
  "name": "requested_action",
  "type": "choice",
  "instructions": "What work does the user request: explain existing code, generate tests, or modify code? Classify the requested outcome, not the files that must be read. Adding test coverage belongs to generate_tests; repairing existing code, including tests, belongs to modify_code. An explanation alone does not request edits.",
  "criteria": {
    "explain": "Understand production or test code without changing it.",
    "generate_tests": "Create additional tests using existing code as reference.",
    "modify_code": "Fix, refactor, or implement production or test code."
  }
}
```

This is candidate wording for experiments, not validated model behavior. Keep it
in a shared JSON definition so the other agent can tune it without editing block
logic. Do not copy a second question definition into Python.

### Declaration and rule

Proposed `building_blocks/questions/requested_action/block.json`:

```json
{
  "name": "requested_action",
  "questions": {
    "requested_action": {
      "question_ref": "requested_action",
      "rule_ref": "requested_action_default"
    }
  }
}
```

Proposed `defaults/rules/requested_action_default.json`:

```json
{
  "name": "requested_action_default",
  "question_type": "choice",
  "conditions": [
    {"field": "answer_confidence", "op": "gte", "value": 0.5},
    {"field": "probability_gap", "op": "gte", "value": 0.15}
  ]
}
```

These thresholds are a provisional starting policy consistent with an existing
choice rule, NOT calibrated for this task. Give this block its own named default
so later tuning cannot accidentally change method selection. Both conditions
must pass. No entropy, model confidence or act_probability gate is added here.
The other experiment work may recommend a different named rule later.

### Output and errors

Return the existing BlockResult. Reducer data has exactly one key, `action`, whose
value is a stable criterion ID or `undecided`. Preserve the runtime's decision
reason instead of translating it into a new custom taxonomy.

Accepted result, rendered as JSON for documentation (actual return is dataclass):

```json
{
  "status": "completed",
  "reason": null,
  "decisions": {
    "requested_action": {
      "answer": "generate_tests",
      "decided": true,
      "reason": null
    }
  },
  "data": {"action": "generate_tests"}
}
```

For a rejected valid prediction: status remains completed; top-level reason is
null; decision answer and data.action are undecided; decision.decided is false;
decision.reason is exactly what the existing conditions evaluator returned.
Do not invent a literal error string in tests: inspect evaluator behavior first.

If a caller's custom preparation explicitly raises SkipBlock, follow existing
skipped behavior: no inference, empty decisions, existing top-level reason and
data.action=undecided. An empty decision map must not crash the reducer.

Invalid input/configuration is an error, not an undecided inference. Preserve
ResponseError, TimeoutError and SDK/loader exception behavior; no automatic retry,
fallback model, or fabricated successful result. Unexpected reducer output is a
BlockExecutionError through existing runtime validation.

## 4. Semantic boundaries for evaluation

The following are intended targets for a later live evaluation dataset; mocks
cannot prove the model understands these sentences.

- E01 “Explain calculateTotal.” => explain.
- E02 “Explain what this spec tests.” => explain.
- E03 “Why does this return null? Do not change anything.” => explain.
- E04 “Explain how you would fix this; don't implement it.” => explain.
- E05 “Write tests for calculateTotal.” => generate_tests.
- E06 “Add missing edge-case tests to invoice.spec.ts.” => generate_tests.
- E07 “Generate tests without changing the service.” => generate_tests.
- E08 “Explain the method and then add unit tests.” => generate_tests.
- E09 “Fix calculateTotal returning a negative result.” => modify_code.
- E10 “Repair the incorrect assertion in this test.” => modify_code.
- E11 “Refactor this method without changing behavior.” => modify_code.
- E12 “Implement an invoice total function.” => modify_code.
- E13 “Fix the service and add regression tests.” => modify_code.
- E14 “Do not add tests; fix the existing test.” => modify_code.
- E15 Same task with relative/full file path => same intended action.
- E16 Same task with unrelated background/noise => same intended action when the
  complete request fits; do not mix truncation effects with semantic errors.

Separately label unresolved cases for discussion; do not silently force them
into the accuracy denominator with arbitrary labels:

- E17 “Review this.” Ambiguous target and output.
- E18 “Fix failing tests.” Modification requested, but production/test edit target
  unknown; expected action modify_code does not claim which file needs changing.
- E19 “Write a test plan only.” Could be explanation/planning vs test generation;
  Sharon has not settled this boundary. Flag taxonomy_pending.
- E20 “Add coverage and repair an existing test.” Mixed generation/modification;
  proposed preference modify_code, but track for explicit taxonomy review.
- E21 “Update README” or non-code requests. Outside this taxonomy.
- E22 “Do that again.” Missing conversational context; prompt-only insufficiency.

Confidence thresholds do not guarantee abstention for E19/E21/E22. A three-choice
model may confidently select an unsuitable option. Report false acceptance. Do
not claim an other/unknown detector exists; adding one requires a new decision.
No heuristic prompt keyword override is authorized to hide such results.

## 5. Execution path and integration

Use existing runtime in this order: resolve question/rule and validate their
types; validate input; prepare/validate payload; predict once through supplied
registry/config; validate response; enrich once; apply rule; extract or abstain;
reduce to data.action; validate output; return BlockResult.

Do not duplicate enrich_prediction, accepts or extract_answer in this block.
Do not recompute raw response metrics in the reducer. The existing logs retain
submitted question/text, model/config, raw response, enrichment, rule and decision.
BlockResult remains compact; do not add raw/enriched payloads to its schema.

Flow usage: a caller passes prompt/config/registry, then branches on data.action.
An undecided result leaves the caller free to do nothing or use its normal path.
The block makes no permission decision and must not equate inferred intent with
authorization to edit. Existing flows/hooks and model defaults remain untouched.

## 6. Proposed file changes

New production files:

- `src/laya_context_router/building_blocks/questions/requested_action/__init__.py`
  only if required by the established package convention.
- `.../requested_action/block.py`: adapter, validators, preparation and reducer.
- `.../requested_action/block.json`: references the question and default rule.
- `.../requested_action/README.md`: contract, examples, overrides, undecided/error
  behavior, semantic limitations, and links to the token-budget handoff.
- `src/laya_context_router/defaults/questions/requested_action.json`.
- `src/laya_context_router/defaults/rules/requested_action_default.json`.

New tests/data:

- `tests/test_requested_action_block.py`: default happy path and validation.
- `tests/test_requested_action_contract.py`: overrides, state and errors.
- `tests/test_requested_action_integration.py`: registry, logging, packaging and
  minimal caller composition; reuse existing utilities rather than new frameworks.
- `tests/fixtures/requested_action_responses.json`: valid SDK-boundary fixtures.
- `tests/fixtures/requested_action_prompts.json`: semantic cases with clear status
  (settled/provisional/taxonomy_pending), expected labels where settled, and notes.

Documentation:

- Keep this plan temporary and out of the implementation final tree. Put the
  verification evidence and test-ID mapping in the implementation PR description
  or an attached report, not a permanent repository copy of this plan.
- Link the new block from the existing appropriate documentation index if needed.

No experiments are required in this implementation bundle. Coordinate with the
other experiment agent before editing any experiments files. Do not modify old
blocks, old rules, flow dispatchers, hook configuration, extraction utilities,
packaging backend or shared runtime without Astra review and recorded justification.
Existing package-data globs appear sufficient; verify before changing pyproject.

## 7. Test plan: deterministic functionality

Mock ONLY the agent loader/predict boundary. The real catalog, Block runtime,
question validation, response validation, enrichment, rule evaluator and extractor
must run. Do not mock the entire block or fabricate its final decisions.

Use full valid prediction envelopes from existing fixtures/schema. For a clear
winner use probabilities .80/.15/.05, choice matching .80, and answer_confidence
.80. Include existing required fields; do not assume the example probabilities
alone are a complete SDK response. Fixtures are synthetic, clearly labeled.

### Contract and happy paths

- T01 each of the three labels wins in a parameterized SDK response; accepted
  decision and data.action match exactly.
- T02 captured prediction input equals original nonblank prompt byte-for-byte.
- T03 surrounding whitespace/newlines preserved; blank-only rejected.
- T04 Unicode/Hebrew, quotes, slashes and filenames preserved as plain input.
- T05 missing prompt/null/number/bool/list/non-object input rejected before load.
- T06 unknown input fields rejected before load, including implementation/code.
- T07 default question instructions/criteria resolved from catalog JSON; capture
  exact submitted local key and three IDs; no duplicated Python definition.
- T08 constructing/catalog-loading block does not instantiate a model.
- T09 one block invocation makes one predict call; enrichment executes once for
  the sole answer (wrap real function if counting, never replace its calculation).
- T10 reducer returns only action; output validator rejects an unknown action.
- T11 input, overrides and synthetic raw response remain unchanged after run.
- T12 SDK-provided extra metadata survives existing validation as appropriate,
  but does not leak into compact data or change the selected action.

### Rule evaluation and abstention

- T13 .80/.15/.05 with answer_confidence .80 passes provisional default.
- T14 .49/.30/.21 rejects for answer-confidence while gap would pass.
- T15 .55/.45/.00 rejects for gap while answer-confidence would pass.
- T16 .50/.35/.15 tests both inclusive boundaries at once; follow existing metric
  rounding behavior, never introduce a private epsilon to make this test pass.
- T17 .499/.300/.201 and .500/.351/.149 separately test just below thresholds.
- T18 tied leaders .50/.50/.00 reject; model choice cannot bypass zero gap.
- T19 rejected valid response is completed + undecided, not skipped or exception.
- T20 exact decision reason matches existing evaluator; top-level reason stays null.
- T21 missing gated metric follows existing evaluator's rejection semantics;
  inspect enrich/evaluator first rather than making missing confidence zero.
- T22 changing unrelated confidence/act_probability leaves outcome unchanged
  when default gated fields are constant; do not accidentally add a gate.
- T23 stricter/looser compatible named rules produce different accept/reject
  outcomes from the SAME copied SDK response on separate calls. No extra call
  per execution; no claim these are different live model predictions.

### Overrides and configuration

- T24 compatible rule override used; default rule JSON remains unchanged.
- T25 wrong-type rule logs rule_type_mismatch and fails before agent load.
- T26 unknown rule/question refs and unknown override keys fail before load.
- T27 full question override with same labels/type changes captured instructions.
- T28 shared reference override works with injected catalog and stable labels.
- T29 question type change rejected before load.
- T30 added/missing/renamed label rejected by block-specific prepared validation.
- T31 malformed criteria/descriptions rejected by existing question validation.
- T32 custom preparer can deliberately change submitted text while preserving
  the question contract; original input remains unchanged.
- T33 custom preparer changing keys/type/labels or emitting blank text fails
  before inference; no fallback to default preparation.
- T34 custom SkipBlock makes zero model calls and valid skipped/undecided output.
- T35 changed criteria order retains IDs and correct extraction; no index-based map.

### Model errors, reuse, logs and callers

- T36 invalid raw response: missing answer, wrong type, unknown selected label,
  missing/extra probability key, invalid sum, NaN/infinity => ResponseError.
- T37 loader error, prediction exception and TimeoutError propagate once with no
  retry and no fabricated undecided classification.
- T38 same model/temp/lang in same registry loads once across multiple calls.
- T39 changing model or temperature makes distinct registry entries and forwards
  actual config; use existing RunConfig semantics, not invented SDK kwargs.
- T40 separate registries do not share an agent; failed load is not cached.
- T41 temporary log destination contains block/question IDs, effective rule,
  raw response, enriched gap, and decision in existing event formats.
- T42 invalid input/config logs useful existing errors without claiming inference.
- T43 minimal test-local flow branches accepted explain/generate/modify and
  undecided correctly; no production hook or dispatcher wiring added.
- T44 import and block calls do not invoke TypeScript, subprocesses or target-file
  reads; catalog/package resource reads are permitted. Assert at appropriate
  utility boundaries, do not disable all file access indiscriminately.
- T45 installed wheel includes block JSON/README and shared question/rule. Invoke
  with fake loader outside checkout/PYTHONPATH; verify decision succeeds.
- T46 current legacy and V2 block/runtime/flow-composition tests still pass.

Each test ID must map to a concrete test function/parameterized case or a named
existing test in the implementation PR verification report. Avoid a second copy of generic runtime
tests when existing tests already cover the behavior; include at least one actual
new-block integration for each block-specific contract.

## 8. Semantic evaluation versus functional tests

Synthetic responses prove our pipeline uses the supplied model output correctly.
They do NOT prove that Laya selects the right label from a prompt. Keep those two
results separate in reports and PR descriptions.

Prepare the E-series corpus as data for the other experiment agent. Include short
clean prompts and modest noise variants, explicit negations, test-file mentions,
production-file mentions, and mixed requests. Preserve a held-out set not used
while tuning wording/thresholds. Do not create hundreds of near-duplicate prompts
or call model-generated expected answers ground truth. Sharon reviews unresolved
semantic boundaries before they become strict accuracy targets.

Future opt-in live evidence should capture model/revision, SDK version, requested
temperature, effective question and rule, full raw/enriched answer, selected label,
accept/reject reason, input-length/truncation diagnostics if verified, and expected
label/status. Report confusion counts, wrong accepted answers, and abstentions.
Abstentions must not be counted as correct classifications to inflate accuracy.

No real model call/download is authorized as part of default tests. No assumption
that a model can report its own identity: inspect supported metadata if available,
otherwise distinguish requested model ID from verified loaded-model identity.
Later live evaluation runs on Sharon's Mac and is not a blocking requirement for
the mock-tested first implementation, but is required before claiming accuracy.

## 9. Token-budget boundary

The published Laya-MLX README lists 1,024 total context tokens for the current
`aac6fef/laya-typed-decisions-mlx` default, shared by instructions, choices and
state. Source: https://github.com/mizorewww/laya-mlx/blob/main/README.md
This is a documented default, not a measurement of Sharon's installed SDK.
Exact tokenizer counts, header caps, special-token overhead, truncation behavior
and runtime overrides still need separate investigation. Do not assume 1,024
prompt tokens are safe or use character/line counts as an exact substitute.

The separate handoff is optional background, available to agents sharing this
workspace at:
`/workspace/scratch/aae8a6a84dee/requested-action-plan/laya-token-budget-handoff.md`.
It is not included in this PR, and reading it is not a prerequisite to implementing
this prompt-only block. Do not implement its investigation tasks in this PR.

Version 1 passes the prompt unchanged;
it does not implement a tokenizer, context guard or code attachment. Include a
long-string transport test only to prove our block does not secretly truncate;
label it as transport-only, not proof the real model accepts that length.

If a discovered SDK behavior prevents even the compact default question from
being represented correctly, pause and call Astra. Do not quietly shorten labels,
increase model limits or introduce a token dependency. Record the finding and
smallest revised plan. Explain the prompt-length limitation in the block README.

## 10. Phases and review gates

### Phase A: reconcile current main and establish baseline

Create an isolated branch from fresh main; inspect AGENTS.md, current runtime,
tests, question/rule names, and concurrent experiment changes. Record SHA and
Python/Node/npm versions. Confirm dependencies without touching other agents'
work. Run relevant existing block/runtime/package/flow-composition tests before
changes. Baseline failures go to Astra; do not relabel them as caused by this work.

### Phase B: write failing new-block tests

Start with T01, T02, T05, T07, T13–T20, T25, T30 and T43, then the rest of the
new-block contracts. Run and retain concise red evidence showing the new module
or behavior is absent, not broken fixtures or unrelated environment errors.
Use schema-valid raw responses. Prepare semantic corpus without running Laya.

### Phase C: minimal additive implementation

Add question/rule/declaration and small V2 adapter. Satisfy the red tests using
the existing runtime and registry. Add README with actual I/O, effective defaults,
override examples, rule rejection/error distinction and semantic/token limitations.
No scope block, existing flow changes, model cache redesign or new runner.

### Phase D: integration and full verification

Run the new tests plus existing V2, runtime, packaged-resource and composition
tests. Build the current TypeScript helper before full-suite extraction tests:
`npm --prefix typescript-helper ci` if needed, then
`npm --prefix typescript-helper run build`.
Run `npm --prefix typescript-helper test` and `python -m pytest -q` on the actual
final checkout. Run existing wheel test and the new installed-resource case with
isolated environments. No live inference. Record exact counts/skips/failures and
reason for each limitation. Re-run relevant checks after subsequent code changes.

### Phase E: independent verifier and separate PR

Ask a separate low-cost verifier agent to compare implementation against this
plan and the actual diff, map T01–T46 to evidence in the PR report, inspect fixture validity,
confirm no existing runtime/flow behavior changed, and flag unverified semantic
claims. Verifier must distinguish tests implemented from tests executed.

Fix confirmed issues, consulting Astra for any deviation, and rerun affected
checks. Publish one separate implementation PR with coherent commits; no push
to main and no automatic merge. Do not push every micro-step. Include exact base
and tested SHAs, change summary, verification map, open limitations, and clear
manual evaluation instructions. Remove this temporary plan from the implementation
branch final tree if it was copied there, and verify no duplicate remains. Preserve
all existing tests unless a real approved
contract change justifies updating one; never weaken tests to get green results.

## 11. Mandatory Sol/Astra escalation instructions

Sol implements the approved plan. If a baseline fails, an assumption is false,
tests expose a shared bug, criteria/contract need changing, or any work deviates
from this plan: stop the dependent change and spawn Astra for diagnosis.

Provide Astra: intended behavior/plan section, current SHA, exact failing command
and output, focused diff, reproduction, what was expected versus observed, and
smallest proposed correction. Ask for a recommendation and an updated plan.
Record the decision and evidence. Resume only the work supported by that update.
Do not repeatedly retry, broaden scope silently, alter acceptance thresholds to
hide failures, or change unrelated code. Continue independent safe work if useful.
For major changes to product meaning, compatibility or architecture, stop and
tell Sharon. If Astra is unavailable, report the blocker rather than substituting
an unreviewed redesign. Never claim an agent reviewed work unless it actually did.

## 12. Definition of done

- One additive requested-action block using existing V2 infrastructure.
- Three agreed criterion IDs, compact descriptions and one replaceable typed rule.
- Explicit prompt-only input and stable accepted/undecided output.
- Required deterministic test coverage with red/green evidence and final-suite
  results on the actual implementation checkout.
- No unapproved edits to existing blocks, hooks, flows, shared runtime or experiments.
- README usable by the next agent; semantic corpus and token limitation visible.
- Independent verification and a separate PR, awaiting Sharon's merge decision.
- No claim that mocks establish live Laya accuracy or complete-input processing.

This document is ready to implement when Sharon gives the implementation agent
this PR and instructs it to proceed. Publishing the plan does not authorize its
implementation or merge. Keep this plan out of the implementation final tree.
