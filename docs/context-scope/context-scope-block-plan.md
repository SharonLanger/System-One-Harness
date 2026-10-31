# Context-scope building block — implementation and test plan

Status: PLAN ONLY. This PR contains this Markdown file only. No implementation,
model execution or changes to existing flows are authorized by publishing it.
Date: 2026-10-31.
Repository: https://github.com/SharonLanger/laya-context-router
Reviewed main: `6de4c8eb9691b0594b12bf5cbf2fa67c862b59ad`.
Implementation owner: Sol. Deviation/reasoning reviewer: Astra.

## 1. Start here: standalone PR handoff

The implementation agent may receive ONLY this PR URL. Read the PR description
and this entire file at the PR head; no prior chat or separate handoff is needed.
When Sharon instructs you to implement this plan, create an isolated branch from
fresh main and a separate implementation PR. Recheck applicable AGENTS.md and
current interfaces because other agents are working concurrently.

Keep this plan PR unmerged. Follow the phases, tests, and escalation rules below.
Before finishing the implementation, remove any copied version of this temporary
plan from the implementation branch's final tree; retain the permanent block
README, tests and product documentation. Put test evidence and its ID mapping in
the implementation PR description or an attached report. Do not create a permanent
duplicate of this plan in the repository. Merge only when Sharon authorizes it.
After the implementation is merged, close this plan PR as superseded.

This cleanup keeps the temporary plan out of main's current files. It does not
erase GitHub PR discussion or commit history; no history rewrite is requested.

## 2. Product definition and scope

Given a user prompt about a method, optionally with a previously classified action,
predict which code relationships the request calls for understanding:

1. `method_only`: the selected method itself.
2. `called_methods`: the selected method plus at least one method it calls.
3. `calling_methods`: the selected method plus at least one method that calls it.
4. `both_directions`: the selected method plus callers and called methods.

The existing rule may reject the model answer, yielding `undecided`.

The consumer of code context is the answering assistant. Do not ask what code
the human user needs to read. This block applies to explanations, test generation,
and code modifications. Its question asks what answering the request requires.

It is a classification of intended context scope based on prompt evidence, not
proof that the actual code is sufficient. Without inspecting source, it cannot
know whether a helper is essential, whether callers exist, or whether a complete
flow has been captured. A local request may still require support declarations.

The four choices describe directions of context, NOT a numerical depth scale.
Callers are not inherently deeper than callees. Do not substitute a score or
convert this into shallow/medium/deep labels.

### Explicit non-goals

- No code reading, AST traversal, file resolution or method selection.
- No retrieval of callers/callees or production context assembly.
- No automatic hook/flow integration or edits to existing flows.
- No implementation or changes to block 1 (requested action).
- No multi-label, top-two or above-average answer-selection rule.
- No recursion limit, context budget allocation, rendering or read-tool hints.
- No classification of answer length; “detailed” alone does not imply callers.
- No “no code needed” choice in this version; it was considered, not retained.
- No new token-budget utility, tokenizer dependency or shared runtime refactor.

## 3. Existing architecture to reuse

At the reviewed main, these files establish the integration:

- `src/laya_context_router/block_runtime/runtime.py` and `contracts.py` provide
  Block, PreparedInput, BlockResult, SkipBlock and typed exceptions.
- `block_runtime/README.md` documents composition, named rules, full question
  overrides, custom preparation, copied inputs, and one prediction per execution.
- `building_blocks/questions/ticket_triage_v2/block.py` supplies the small adapter
  pattern with explicit config/registry and optional catalog injection.
- `defaults/questions/department.json` demonstrates reusable choice definitions.
- `defaults/rules/method_selection_default.json` demonstrates an AND policy on
  answer_confidence and enriched probability_gap.
- `laya/predict.py` validates raw answers and allowed criteria/probabilities.
- `laya/registry.py` reuses agents by model/temperature/language within a supplied
  registry; it does not create a process-independent cache.
- `pyproject.toml` includes block JSON/Markdown and shared question/rule resources
  through wildcard package-data patterns.

Existing test anchors: `tests/block_runtime/test_runtime.py`,
`tests/block_runtime/test_wheel.py`, `tests/test_v2_blocks.py`,
`tests/test_v2_flow_composition.py` and `tests/test_packaged_blocks.py`.
No AGENTS.md was present in the reviewed remote tree; check again before editing.

Block 1's plan is https://github.com/SharonLanger/laya-context-router/pull/19 .
That link is background, not an implementation dependency. This block can run
without block 1 installed and must not import or invoke it internally.

## 4. Proposed input contract

Proposed entry point:

```python
from laya_context_router.building_blocks.questions.context_scope.block import run

result = run(
    {"prompt": "Explain where calculateTotal is used during checkout.",
     "requested_action": "explain"},
    config=config,
    registry=registry,
    # Optional existing extension points:
    # rule_overrides={"context_scope": "another_choice_rule"},
    # question_overrides={"context_scope": complete_question_body},
    # prepare_input=custom_preparer,
    # catalog=custom_catalog,
)
```

Require a dict containing `prompt`, a nonblank string. An optional
`requested_action` may be `explain`, `generate_tests`, `modify_code`, `undecided`
or null. Omitted/null/undecided means no usable prior action, so classify from the
prompt alone. Reject other values and unknown input keys before model loading.
Reject missing/null/nonstring/whitespace-only prompts. Preserve the exact text
of valid prompts, including whitespace, Unicode, filenames and quoted content.

No file path, method implementation or signature field in version 1. References
already present in the prompt remain text. A selected-method identifier may be
needed by a later flow, but is not needed to classify the request's relationship
intent. Do not introduce a filesystem dependency to interpret names here.

### Default preparation

When there is no usable action, submit the original prompt unchanged as text.
When a known action is provided, serialize a small JSON object as the input text:

```json
{
  "prompt": "Explain where calculateTotal is used during checkout.",
  "requested_action": "explain"
}
```

Use standard JSON serialization with Unicode preserved, rather than concatenating
unescaped fragments or using ad hoc delimiters. Tests should decode the captured
JSON and verify exact values, not prescribe incidental whitespace formatting.
Do not append probabilities, confidence, reasons or raw block-1 output. The action
is optional context, not an instruction and not ground truth. The prompt remains
the primary evidence. An explanation can need any of the four scopes; generating
tests does not automatically require called_methods or both_directions.

Return PreparedInput(text, resolved_questions, {}). The reducer must not rely on
state to determine scope. Keep the local question key `context_scope` stable.

Custom preparation may intentionally alter text, but must produce nonblank text
and preserve the one-question, choice-type, exact-four-label contract. Use the
existing validate_prepared hook for only these domain checks. Do not duplicate
generic runtime validation or require custom text to equal the default encoding.

## 5. Proposed question and choices

Use the accepted wording with a small clarification that the selected method is
included in every relationship choice. Keep labels/descriptions in shared JSON.

Proposed `defaults/questions/context_scope.json`:

```json
{
  "name": "context_scope",
  "type": "choice",
  "instructions": "Does answering this request require understanding the method itself, what it calls, how it is used, or both directions? Each relationship option includes the method itself. Use the user's request as primary evidence; any supplied action is context only. Detail alone does not imply broader relationships.",
  "criteria": {
    "method_only": "Understand the selected method's own implementation and behavior.",
    "called_methods": "Understand this method and at least one method it calls.",
    "calling_methods": "Understand this method and at least one of its callers.",
    "both_directions": "Understand this method together with callers and called methods."
  }
}
```

Candidate wording is configurable and not yet validated on live Laya. Do not add
examples to every production request before measuring their token cost. Do not
include other question variants by default; later experiments can override the
full question body while preserving the contract.

### Choice boundaries

- `method_only` means the request concerns behavior within the method. It does
  not certify that a signature alone suffices or that source dependencies vanish.
- `called_methods` means at least one call leaving the selected method's own
  implementation matters, including a call made inside an inline callback.
- `calling_methods` means usage, entry points or upstream invocation matters.
- `both_directions` represents both kinds of relationships plus the method itself.
  It does not mean all files, all callers/callees, unlimited recursion or full
  implementation of everything reachable.

Names such as “external” can be confusing: callees may be in the same file or
another file. Avoid implying only external packages count. Inline callback bodies
are not standalone context targets, but calls from them can be relevant.

These labels overlap in their included code, but should describe distinct requested
relationship scopes. The model chooses one scope; it is not an independent
probability of relevance for each individual method.

## 6. Declaration, rule and output

Proposed `building_blocks/questions/context_scope/block.json`:

```json
{
  "name": "context_scope",
  "questions": {
    "context_scope": {
      "question_ref": "context_scope",
      "rule_ref": "context_scope_default"
    }
  }
}
```

Proposed `defaults/rules/context_scope_default.json`:

```json
{
  "name": "context_scope_default",
  "question_type": "choice",
  "conditions": [
    {"field": "answer_confidence", "op": "gte", "value": 0.5},
    {"field": "probability_gap", "op": "gte", "value": 0.15}
  ]
}
```

Thresholds are provisional, copied as a starting convention from an existing
choice policy, not calibrated recommendations. A separate rule name isolates
future tuning. Both conditions must pass. No additional entropy, confidence or
act_probability gate, no label re-ranking and no summed probabilities.

Support named compatible rule overrides and full question overrides using the
existing runtime. A question override may change wording/descriptions but must
retain choice type and exactly the four IDs. Missing refs, unknown override keys,
wrong-type rules, or changed criterion IDs fail before inference. No inline rules
or deep-merge behavior is added.

Return the standard BlockResult; reducer data has exactly one key, `scope`.

Accepted result shown as JSON (actual API returns the existing dataclass):

```json
{
  "status": "completed",
  "reason": null,
  "decisions": {
    "context_scope": {
      "answer": "calling_methods",
      "decided": true,
      "reason": null
    }
  },
  "data": {"scope": "calling_methods"}
}
```

Rejected valid prediction: status=completed, top-level reason=null, decision
answer=undecided, decided=false, decision.reason preserved verbatim from the
existing rule evaluator, and data.scope=undecided. Do not collapse undecided to
method_only or fetch everything as an implicit fallback.

Custom SkipBlock: preserve status=skipped and its reason, empty decisions, no
model call, data.scope=undecided. Other input/config errors and SDK errors remain
errors, not successful abstentions. Preserve TimeoutError/ResponseError/loader
exceptions; no retries or fallback model. Unknown reduced scopes must be rejected
by output validation through BlockExecutionError.

## 7. Execution and later flow composition

Reuse the existing path: resolve/validate question and rule -> validate input ->
prepare/validate -> predict once -> validate response -> enrich once -> apply
one rule -> extract accepted answer or undecided -> reduce/validate output.

Do not copy enrichment/rule/extraction into the block. Do not reconstruct gaps
from logs. Use the existing diagnostic events, including the raw response,
enriched prediction, effective question/rule/config and final decision. Keep
BlockResult compact; no new raw-response storage system.

A future flow may call block 1, pass its accepted action into this block, and then
choose a utility. If block 1 is undecided, it may still call this block with the
prompt alone. This is caller orchestration, not an internal dependency. If block
1 becomes available during implementation, an optional composition test may use
its real adapter with fake SDK responses; don't import unmerged feature code.

Future context retrieval is illustrative only: method_only could use method
extraction; called_methods could consult outgoing calls; calling_methods could
consult incoming calls; both could consult both. This implementation stops at
the scope answer. It does not decide between source code and navigation hints.

## 8. Proposed files and compatibility boundaries

New production resources:

- `src/laya_context_router/building_blocks/questions/context_scope/block.py`.
- `.../context_scope/block.json` and `.../context_scope/README.md`.
- `.../context_scope/__init__.py` only if existing package convention needs it.
- `src/laya_context_router/defaults/questions/context_scope.json`.
- `src/laya_context_router/defaults/rules/context_scope_default.json`.

New tests/data, grouped sensibly rather than one file per case:

- `tests/test_context_scope_block.py`: input, payload, default decision behavior.
- `tests/test_context_scope_contract.py`: overrides, validation and failures.
- `tests/test_context_scope_integration.py`: registry/log/package/caller checks.
- `tests/fixtures/context_scope_responses.json`: synthetic valid SDK responses.
- `tests/fixtures/context_scope_prompts.json`: semantic evaluation corpus.

The block README must explain the four scopes, prompt-only vs action-enriched
payload, actual API/I/O, overrides, abstentions versus errors, model limits and
semantic limitations. Add a small appropriate documentation index link if needed.
Keep this temporary plan out of the implementation final tree.

No shared runtime, model-loader, old block/rule, TypeScript helper, hook dispatcher
or experiments changes are expected. Existing package-data patterns appear
sufficient; verify rather than editing packaging preemptively. If names now
collide or contracts changed, consult Astra before choosing a replacement design.

## 9. Functional test plan

Run the real block, catalog, runtime, validators, enrichment, rule evaluator and
extractor. Fake only the agent loading/prediction boundary. Do not return a final
BlockResult directly from a mock and call that an end-to-end block test.

Use existing response fixtures/schema to build valid synthetic responses. For
each winning scope, use a .80/.10/.06/.04 distribution assigned to the correct
IDs and answer_confidence .80. Include any existing required envelope fields.
The following IDs must map to concrete new/existing tests and execution evidence
in the implementation PR report. Parameterization is preferred over repetition.

### Input and preparation

- C01 Each of four accepted labels maps to the same data.scope and decision.
- C02 Prompt-only input reaches SDK unchanged, including surrounding whitespace.
- C03 Each known action is serialized with exact original prompt in valid JSON.
- C04 Omitted/null/undecided action all produce the same prompt-only payload.
- C05 Quotes, newlines, braces, Unicode/Hebrew and file paths survive serialization.
- C06 Missing/null/nonstring/blank prompt rejected before loader/predict.
- C07 Invalid action type/value/case and unknown input keys rejected before load.
- C08 Input/overrides/question definitions remain unchanged after execution.
- C09 No file access based on prompt references, subprocess, AST or TypeScript
  call; allow legitimate catalog/package resource reads.
- C10 Long text passes through unchanged in fake-agent tests; label this transport
  behavior only, not evidence the live model fits the input.

### Runtime, rule and response

- C11 One execution predicts once and enriches its sole answer once; spies wrap
  real behavior rather than replacing the calculation.
- C12 .80/.10/.06/.04 passes; correct stable ID survives criteria-order changes.
- C13 .49/.25/.16/.10 rejects confidence even though gap passes.
- C14 .55/.45/.00/.00 rejects gap even though confidence passes.
- C15 .50/.35/.10/.05 verifies inclusive threshold boundaries using existing
  rounding semantics; no ad hoc epsilon or policy changes to force green.
- C16 .499/.300/.151/.050 and .500/.351/.099/.050 separately test just below
  confidence and gap thresholds; probability sums must stay valid.
- C17 .50/.50/.00/.00 tie rejects; no arbitrary tie selection accepted.
- C18 Rule rejection remains completed/undecided with exact evaluator reason.
- C19 Same copied raw response under compatible looser/stricter rules yields
  accepted vs undecided on separate runs; rules never change the model label.
- C20 Unrelated confidence/act_probability changes do not create a hidden gate.
- C21 Missing gated metric follows existing enrichment/evaluator semantics;
  inspect those before writing expected assertions, never invent zero values.
- C22 Missing answer/wrong type/unknown choice/probability key mismatch/bad sum/
  NaN/infinity produce existing ResponseError, never successful undecided.
- C23 Loader/predict failures and TimeoutError propagate without retries.
- C24 Output validator rejects unknown scope or unexpected data fields; rejected
  prediction never falls back to method_only or both_directions.

### Configuration and extension points

- C25 Default declaration resolves shared question/rule JSON without loading agent.
- C26 Same-label complete question override changes actual submitted wording.
- C27 Shared question-ref override works through injected catalog.
- C28 Type-changing question override or wrong-type rule fails before model load;
  wrong-type rule logs the existing rule_type_mismatch event.
- C29 Added/missing/renamed criteria fail block-specific prepared validation.
- C30 Unknown refs, unknown override keys and malformed question body fail early.
- C31 Custom preparation may change input text but must preserve question schema.
- C32 Invalid custom prepared text, names, type or labels fail before prediction.
- C33 Custom SkipBlock yields skipped/empty decisions/undecided data and no call.
- C34 A run with custom overrides does not contaminate a later default run.

### Integration and regression

- C35 Same model/temp/lang reuses one agent within registry across calls; changed
  model/temp/lang use distinct entries with correct requested configuration.
- C36 Separate registries do not share agents and failed loads are not cached.
- C37 Existing temporary-log capture shows effective payload/action, question,
  named rule, raw answer, enriched gap and final decision under this block ID.
- C38 Test-local caller branches on four scopes and undecided without actual
  retrieval; keep all production flows unchanged.
- C39 Simulated block-1 accepted/undecided results map to optional action input
  without calling block 1 inside this block. Do not claim an unimplemented
  block-1 adapter was integration-tested.
- C40 Installed-wheel run outside checkout/PYTHONPATH can load this block and
  its question/rule/README resources and classify via a fake agent.
- C41 Existing legacy/V2 block, runtime, packaging and composition tests pass;
  full final checkout suite passes or failures are explained and escalated.

Reuse coverage already established by generic tests where appropriate, but do
not omit new-block-specific input/criteria/output checks. Never modify existing
tests simply to accommodate an accidental regression.

## 10. Semantic evaluation cases for later experiments

These describe intended classification targets, not guaranteed model results.
Include clean examples and short irrelevant-noise paraphrases within measured
limits. Keep a held-out set. Do not use mocked answers as evidence of semantic
accuracy. Record unresolved meanings separately instead of inventing ground truth.

- S01 “Explain the arithmetic inside calculateTotal.” -> method_only.
- S02 “Explain every line inside this method; skip its dependencies.” -> method_only.
- S03 “Write unit tests for this method's own boundary conditions; mock helpers.”
  -> method_only (candidate target; mock setup may still need helper signatures).
- S04 “Explain how calculateTotal uses calculateDiscount.” -> called_methods.
- S05 “Test this method together with the helper it invokes.” -> called_methods.
- S06 “Explain the normalize call made inside this method's map callback.”
  -> called_methods; callback nesting does not remove the relation.
- S07 “Which methods call calculateTotal, and why?” -> calling_methods.
- S08 “Explain where this method is used during checkout.” -> calling_methods.
- S09 “Test how the controller invokes this method; mock downstream helpers.”
  -> calling_methods (candidate target).
- S10 “Trace who invokes this method and what it invokes.” -> both_directions.
- S11 “Test the caller through this method into its downstream service.”
  -> both_directions.
- S12 “Fix this method while preserving its callers and helper interactions.”
  -> both_directions (candidate target).
- S13 “Explain the callers, not what this method calls.” -> calling_methods.
- S14 “Explain the called helpers, not the callers.” -> called_methods.
- S15 “Explain this method in detail.” -> method_only as requested scope, not
  a verified claim that the body alone suffices.
- S16 “Write very detailed tests.” -> ambiguous without target/relationships;
  mark taxonomy_pending rather than automatically choosing both_directions.
- S17 “Explain the full flow.” -> ambiguous without relation to a selected method;
  do not create a hidden full_flow label.
- S18 “Explain it.” -> missing context; mark prompt_insufficient.
- S19 “What is a TypeScript interface?” -> out_of_scope; there is no no-context
  category, and a confidence rule cannot guarantee semantic abstention.
- S20 “List direct callers.” -> calling_methods even if implementation context
  later proves unnecessary; scope classification is not a command to attach body.
- S21 Same explicit relation request with different optional action values:
  scope should remain grounded in prompt; capture action-bias errors.
- S22 Same intent with path/no path or modest background noise -> same expected
  scope if all input is retained; measure truncation separately.

All candidate/provisional cases need human review before strict accuracy scoring.
Mixed-direction requests must be representable by both_directions without fetching
all relationships. Two large choice probabilities may mean uncertainty, not two
independently relevant scopes. Do not apply top-two/above-average extraction here.

Future live reports should capture actual model/SDK version, requested temperature,
question/rule, input representation, raw/enriched answer, selected/accepted scope,
reason and expected label/status. Report false accepted scopes and abstentions
separately. No real model calls or downloads in default tests; Sharon runs explicit
live evaluation on Mac. This implementation can be complete while live accuracy
remains unmeasured, provided that limitation is explicit.

## 11. Token-budget limitation and parallel work

The Laya-MLX maintainer README lists 1,024 total context tokens for the existing
typed-decisions model, including instructions, choices and state:
https://github.com/mizorewww/laya-mlx/blob/main/README.md .
Other models/configurations differ. Header caps, special tokens, actual tokenizer,
truncation behavior and Sharon's installed SDK remain separate verification work.
Do not equate this with 1,024 prompt tokens or a fixed number of code lines.

This block adds only a small optional action field and a compact question, but
that still consumes capacity. It has no verified token guard of its own. Document
the limitation and do not silently trim text. Another agent is planning model
loading and per-model budgets. Do not duplicate that work or guess its future API.
If a compatible guard lands in the existing prediction path, use it normally and
preserve its errors. Ask Astra if its contract requires changes to this plan.

## 12. Phases, checks and handoff

### A. Baseline

Read fresh main and applicable instructions; record actual SHA/tool versions and
parallel changes. Confirm question/rule names and current overrides. Run relevant
existing runtime/block/packaging/composition tests before edits. Escalate baseline
failures rather than silently ignoring them or rewriting unrelated code.

### B. Test first

Add failing tests for C01–C08, C11–C18, C28–C33 and C38 first; then complete the
remaining coverage. Record clear red evidence caused by the absent new behavior,
not invalid fixtures or missing dependencies. Prepare semantic corpus as data
only. Do not load a real model or adjust expectations to mimic mock output.

### C. Minimal additive implementation

Add shared question/rule, block declaration and adapter using existing runtime.
Implement strict input, custom-prepared contract and output validation. Keep
raw/enrichment/rules in the existing execution path. Add permanent README with
real examples, optional action encoding and limitations. No flow wiring.

### D. Integration and final verification

Run all new tests and existing targeted V2/runtime/package/composition tests.
Build current helper before full-suite extraction checks:
`npm --prefix typescript-helper ci` when dependencies need installation, then
`npm --prefix typescript-helper run build`.
Run `npm --prefix typescript-helper test` and `python -m pytest -q` against the
actual final checkout. Execute the isolated-wheel/resource check. Record exact
commands, results, skips and failures; no claim based on an older copied baseline.
After further code changes, rerun affected checks. No live inference required.

### E. Independent verification and PR

Use a separate low-cost verifier to compare the final diff with this plan, map
C01–C41 to actual test evidence, inspect fixtures, confirm existing APIs/flows
remain intact, and distinguish semantic promises from tested functionality.
Record unresolved issues honestly. Fix reviewed defects and rerun affected checks.

Remove any copied temporary plan before finishing the implementation PR, retaining
the permanent README/tests. Publish coherent commits in a separate PR, not main;
do not push every small edit. Describe tested SHA, validations, live limitations,
Astra decisions and caller examples. Await Sharon's merge instruction. After merge,
close the temporary plan PR. Do not delete unrelated plans from other agents.

## 13. Mandatory Sol/Astra escalation

Sol performs the approved implementation. Any failed baseline/check, false
assumption, shared bug, needed scope change or deviation requires asking Astra
before proceeding with the dependent change. Supply the plan section, actual SHA,
exact reproduction/error, relevant diff, expected vs observed behavior and smallest
proposed correction. Ask Astra for diagnosis, next action and a revised plan.

Record the advice and validate it with tests. Do not endlessly retry, weaken
assertions, silently expand scope, change labels or tune thresholds to hide a
failure. Continue unrelated safe work if useful. For major product/compatibility
changes, stop and explain the issue to Sharon. If Astra is unavailable, report
the blocker instead of improvising a broader redesign. Never claim a review or
test ran unless it actually did.

## 14. Completion criteria

- New reusable block, with one choice question and one overrideable typed rule.
- Optional action enrichment; no dependency on block 1 execution.
- Exactly four stable scopes or rule-based undecided, with clear errors.
- Existing runtime reused; no code retrieval, hook integration or multi-selection.
- Test-first and final-suite evidence for the actual implementation checkout.
- Permanent README, semantic corpus, independent verifier and explicit limitations.
- Implementation PR excludes this temporary plan; merge remains user-controlled.

This plan is ready for implementation when Sharon gives the agent this PR and
instructs it to proceed. Creation of the plan PR is not implementation approval.
