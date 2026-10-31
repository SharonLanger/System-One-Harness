# Building-block design and contracts

All APIs below are proposed. This is not a claim that these interfaces exist yet.

## 1. Vocabulary and ownership

A question is one typed request to Laya. A rule decides whether its answer is
acceptable. A question block prepares one or more questions and optionally reduces
their decisions into a useful domain result. A flow chooses blocks, calls utilities,
branches and decides what to send onward. A deterministic utility need not call Laya.

Keep two layers explicit: shared execution does validation/predict/enrichment/rules;
block-owned code defines its input contract, prepares payloads and reduces decisions.
Use composition and small functions, not subclass requirements.

## 2. Proposed files

Under `src/laya_context_router/`:

- `block_runtime/__init__.py`: public V2 runtime exports.
- `block_runtime/runtime.py`: the shared run sequence.
- `block_runtime/contracts.py`: PreparedInput, BlockResult and typed errors.
- `block_runtime/catalog.py`: load/resolve named questions and rules.
- `block_runtime/README.md`: API, lifecycle, extension examples and error contract.
- `defaults/rules/*.json`: one typed rule per file.
- `defaults/questions/*.json`: one complete reusable question definition per file.
- `defaults/README.md`: names, types and how to add defaults.
- `building_blocks/questions/ticket_triage_v2/`: block.json, block.py, README.md.
- `building_blocks/questions/method_selection_v2/`: same files.

Keep current blocks.py, existing block folders and old JSON files through parity.
Do not make a second package called blocks beside blocks.py. One shared defaults
catalog, resolved using package resources; never relative to process cwd. Inject
an alternate catalog directory in tests if useful, not arbitrary path references
from block JSON. Register code functions explicitly in Python.

## 3. Rule definition and type compatibility

Proposed `defaults/rules/method_selection_default.json`:

```json
{
  "name": "method_selection_default",
  "question_type": "choice",
  "conditions": [
    {"field": "answer_confidence", "op": "gte", "value": 0.5},
    {"field": "probability_gap", "op": "gte", "value": 0.15}
  ]
}
```

Exactly one supported type per new rule: choice, noul or score. Conditions are
ANDed, using existing operators and missing-field handling. A supplied override
replaces the default rule for that question entirely; never merge thresholds.
A score rule cannot be applied to choice even if both contain probability_gap.
No wildcard compatibility or implicit fallback. An intentionally empty conditions
list means accept any structurally valid answer; document that explicitly.

Reuse RulesConfig/evaluate_conditions by translating the typed wrapper into the
existing condition representation. Preserve old RulesConfig callers unchanged.
For migrated type-specific policies flatten common conditions plus the matching
conditions_by_type entry into the new typed list, in original evaluation order.
Do not guess a legacy policy's type from metric names; assign it from the actual
question it belongs to. New typed files need no conditions_by_type nesting.

Validate obvious field/type mistakes (e.g. distance_from_boundary on choice,
probability_gap on noul) before prediction. Maintain a small list of supported
existing metrics, including confidence, answer_confidence, action.act_probability,
probability_gap, normalized_entropy and distance_from_boundary as applicable.
The actual allowlist must be checked against existing shipped policies before
migration; do not silently drop a legitimate existing field. A compatible metric
may still be absent in an actual response: retain undecided/missing-field behavior.
Thresholds/operators are validated, but do not claim they are calibrated.

## 4. Shared or block-owned questions

A shared question file contains name, type, instructions and criteria when needed,
using the current Question schema. Example `user_intent.json` is illustrative only:

```json
{
  "name": "user_intent",
  "type": "choice",
  "instructions": "Which kind of help is the user requesting?",
  "criteria": {"explain": "Explain existing code", "change": "Modify existing code"}
}
```

Do not ship this as a new feature during migration. Start with existing questions.
Dynamic method question defaults keep the existing none_or_unclear sentinel;
preparation fills the file's method choices before model invocation.

Example method-selection block.json:

```json
{
  "name": "method_selection",
  "questions": {
    "method": {
      "question_ref": "method_selection",
      "rule_ref": "method_selection_default"
    },
    "multiple_relevant": {
      "definition": {
        "type": "noul",
        "instructions": "Does the request require explaining more than one candidate callable?"
      },
      "rule_ref": "multiple_methods_default"
    }
  }
}
```

Exactly one of question_ref/definition; rule_ref is required. Outer keys are the
local answer names. A shared question's catalog name may differ: bind its body
to the local name before SDK validation. Duplicate local names or catalog names
are errors, including duplicate JSON keys. References are names, not paths.
Input/output contracts are Python validators and documented examples, not strings
that pretend to be executable JSON schemas. Avoid a schema framework for this demo.

## 5. Public call and overrides

Proposed generic call (names finalized in implementation phase 1):

```python
result = block.run(
    input_data,
    config=RunConfig(model="model-A", temperature=0.2),
    registry=registry,
    rule_overrides={"method": "method_selection_strict"},
    question_overrides=None,
    prepare_input=None,
)
```

Config and registry remain required from the caller: one clear source of model
settings, with no competing model default hierarchy. The same registry caches
by model/temperature/language during this invocation. Distinct calls may use
other models/configs. All questions in one block run use that same config; for
per-question models, split into separate block runs in the flow.

Overrides may contain a subset of local question names. Unknown keys fail early.
A question override is a complete question body or a shared question reference,
not an arbitrary deep merge. Its type must equal the declared question type:
reducers and input preparation rely on that contract. To change type, define a
new block. Validate the effective rule after resolving overrides and after
preparation; no request reaches Laya with incompatible types or names.

Runtime copies definitions per call. No changes to catalog objects, input data,
registry settings or original raw response. Default calls after overrides use
unchanged defaults. No configuration inheritance chain.

## 6. Input preparation

MethodSelectionInput (new sibling):

```json
{
  "text": "Explain how calculateTotal works",
  "source_outline": {
    "path": "/project/src/invoice.ts",
    "source_hash": "<actual source hash>",
    "callables": [
      {"id": "<actual outline ID>", "name": "calculateTotal", "signature": "function calculateTotal(): number", "location": {"line": 10, "column": 1}}
    ]
  }
}
```

Actual source_outline is the full existing validated outline, not this abbreviated
example. Keep max_candidates/max_input_chars as validated block options with
current defaults and counting rules. Text must be a string; blank text can remain
allowed by the generic runtime for compatibility, while individual blocks may
state a stricter contract. Do not silently strip, truncate or rewrite prompt text.

Preparation signature:
`prepare_input(validated_input, copied_question_definitions) -> PreparedInput`.
PreparedInput has `text`, `questions` (complete SDK bodies keyed by local names),
and `state` (block-owned mapping for reduction, never sent to Laya).
The method preparer builds readable labels, keeps the source identity map in
state, adds the sentinel and retains budget/ambiguity checks. The reducer validates
that state before mapping a decision to an ID.

Caller-supplied preparation replaces the default function, not the validators.
It receives the same block input contract and must return the same PreparedInput
contract. It can call existing utilities when needed, but cannot alter the local
question set/types or bypass budgets. For genuinely different raw inputs use a
thin adapter: e.g. a flow calls outline(file) then passes the resulting outline.
Do not change the default method block into a mandatory file-reading operation.

Expected no-work conditions (no candidates, candidate budget, ambiguous signatures)
use an explicit SkipBlock(reason, state) signal caught by the runtime. This is not
an error. Unexpected preparation exceptions are logged and propagated as a typed
block failure. Validators run before custom preparation; catalog/rule configuration
errors are detected before utility preparation or agent loading where possible.

TicketTriageInput: {"text": string}. Preparation passes the existing two questions
unchanged; reduction needs no method mapping. Other future blocks explicitly
provide their own input validator, preparer and result validator.

## 7. Runtime lifecycle and output

1. Validate block declaration; resolve defaults and explicit overrides.
2. Validate input and options; validate effective question/rule compatibility.
3. Run preparation, or return a documented skipped result.
4. Validate prepared question names/types/criteria/text/state and input budgets.
5. Call existing predict with the supplied config/registry exactly once.
6. Validate response using existing behavior. Enrich each requested prediction once.
7. Evaluate one rule and extract answer with existing choice/noul/score semantics.
8. Reduce decisions into block-specific data; validate returned data.
9. Return the result and log completion.

Do not call existing interpret on already enriched answers if it enriches again.
Initially keep legacy interpret intact; V2 composes existing enrich_prediction,
accepts and extract_answer. Share a small pure primitive later only if tests
justify it. For choice extract the SDK choice; do not recompute argmax. For noul
preserve current >=0.5 yes behavior. Preserve score rounding/clamping/legend.
Rules reject with undecided; they do not choose another answer.

Proposed BlockResult (successful run with rejected method choice):

```json
{
  "status": "completed",
  "reason": null,
  "decisions": {
    "method": {"answer": "undecided", "decided": false, "reason": "below_threshold:probability_gap"},
    "multiple_relevant": {"answer": "no", "decided": true, "reason": null}
  },
  "data": {
    "selected_id": null,
    "reason": "method_undecided",
    "candidate_map": {},
    "label_map": {}
  }
}
```

Maps above are abbreviated. `completed` means execution succeeded, not all answers
were accepted. `skipped` means no model call, with nonempty reason, empty decisions,
and block-specific state/data defined by that block. SDK/config/validation failures
raise typed exceptions rather than look like ordinary undecided answers.
Return compact decisions/domain data. Keep raw/enriched payloads in existing DEBUG
logs; don't introduce a persistent store or huge result envelope in this change.

Legacy adapters restore exactly the previous returned dictionaries: ticket triage
returns decisions only; method selection returns selected_id/reason/decisions/
candidate_map/label_map. Existing consumers must not suddenly receive BlockResult.
Document new interface for new callers and compatibility interface for old callers.

## 8. Errors and useful logging

Use small ValueError-compatible configuration/input error types, plus a block
execution error preserving its cause. Retain TimeoutError propagation so the flow's
deadline behavior is unchanged. Old adapters preserve documented exception classes
where tests rely on them. A flow decides whether to stop, branch or map failure to
no-op; the block never silently retries another model or substitutes another rule.

Required ERROR fields: block name, stage, question name if applicable, selected
rule name, expected/actual question type and stable error code. Type mismatch uses
`rule_type_mismatch`; missing rule uses `rule_not_found`; invalid prepared input
uses `invalid_prepared_input`. Log selected effective rules/config at DEBUG, model
response/enrichment using existing logs, and compact final decisions at INFO.
No secrets, raw prompts or full source in error messages. Avoid new logging system.

## 9. Using blocks in a flow

Illustrative Python control flow, not an additional framework:

```python
registry = AgentRegistry(real=True)  # Tests supply an explicit fake loader.
intent = intent_block.run({"text": prompt}, config=config_a, registry=registry)
if intent.decisions["intent"]["answer"] == "explain":
    file = resolve_file_reference(prompt)
    source_outline = outline(file)
    selection = method_block.run(
        {"text": prompt, "source_outline": source_outline},
        config=config_b, registry=registry,
        rule_overrides={"method": "method_selection_strict"},
    )
    if selection.data["selected_id"] is not None:
        return extract_callable(file, selection.data["selected_id"])
return None
```

Intent block and resolver shorthand are illustrative future blocks/functions.
Actual tests use tiny fixture blocks plus existing outline/extraction utilities.
No new intent feature is required. Flow must inspect decided/status, not treat
undecided as no. A second question round is another explicit block call; same
registry permits agent reuse. Flow owns cross-question AND/OR decisions. The method
reducer retains its existing requirement of accepted method plus accepted
multiple_relevant=no. One question's rejection must not erase another decision.
