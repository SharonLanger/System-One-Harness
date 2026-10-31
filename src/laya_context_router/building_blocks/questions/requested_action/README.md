# Requested action

Classify the requested outcome from one prompt using the existing V2 runtime.
This block is additive; no production hook or flow invokes it automatically.

```python
from laya_context_router.building_blocks.questions.requested_action.block import run
from laya_context_router.laya.config import RunConfig
from laya_context_router.laya.registry import AgentRegistry

# The caller supplies and owns the invocation's registry.
# Use an injected loader in tests; real=True only for deliberate live execution.
registry = AgentRegistry(real=True)
result = run({"prompt": "Write tests for calculateTotal in invoice.ts."},
             config=RunConfig(), registry=registry)
# result.data == {"action": "generate_tests"} if that label is accepted
```

Input is exactly `{"prompt": nonblank_string}`. Missing/extra keys and nonstring
or blank values raise BlockInputError before agent loading. The original text,
including surrounding whitespace, Unicode and filenames, passes unchanged.
Filenames are text; the block reads no target files or TypeScript outlines.

One `requested_action` choice question has three stable IDs:

- `explain`: understand production or test code without changing it.
- `generate_tests`: create additional tests using existing code as reference.
- `modify_code`: fix, refactor or implement production or test code.

The question lives in `defaults/questions/requested_action.json`; block.json
references it. The separate `requested_action_default` typed rule requires both
`answer_confidence >= 0.5` and enriched `probability_gap >= 0.15`, inclusive.
These thresholds and the question wording are provisional, not calibrated.
Model confidence and act_probability are not default gates.

Returns the existing BlockResult. Accepted output has status `completed`, null
top-level reason, one decision, and exactly `data={"action": <stable ID>}`.
Rule rejection also completes successfully, with action/answer `undecided`,
`decided=False`, and the existing evaluator's decision reason, such as
`below_threshold:probability_gap` or `field_missing:answer_confidence`.
A caller's SkipBlock yields status `skipped`, its top-level reason, empty decisions,
and `data={"action": "undecided"}`. Invalid input/configuration and malformed SDK
responses are errors. Loader errors, SDK exceptions and TimeoutError propagate;
there is no retry, fallback model or fabricated classification.

```python
result = run(
    {"prompt": prompt}, config=config, registry=registry,
    rule_overrides={"requested_action": "my_choice_rule"},
    question_overrides={"requested_action": full_choice_question},
    catalog=my_catalog,
)
```

Named rules must exist in the supplied catalog and be choice-compatible. Question
overrides may be a full definition or a catalog reference. They can change
instructions/descriptions/order but must retain the same type and three IDs.
A full definition contains `type`, `instructions`, and `criteria` (see the default
JSON). There is no inline rule merge. Defaults and caller inputs remain unchanged.

Custom `prepare_input(value, questions)` can explicitly replace the submitted
text and return PreparedInput; text must stay nonblank and question names, type,
and labels must remain valid. Custom state does not determine the result.
Construction/catalog access is lazy with respect to model loading. Each run uses
one prediction and one enrichment; caller-owned registry reuse follows existing
model/temperature/language caching semantics. Existing debug logs retain effective
configuration, question, raw response, enriched metrics and decision.

Callers can branch on `result.data["action"]` and use their normal path on
`undecided`. Intent is not authorization. In particular `modify_code` does not
establish that production code is the edit target.

## Evaluation and input limits

Run deterministic tests with `python -m pytest -q tests/test_requested_action*.py`.
Synthetic SDK envelopes prove transport, validation, rule evaluation and extraction,
not live Laya classification accuracy. `tests/fixtures/requested_action_prompts.json`
contains E01–E22, including a held-out split and unsettled cases excluded from
accuracy scoring. Do not tune using the held-out split. Mixed test generation and
repair remains a taxonomy review case. Out-of-taxonomy and context-dependent
prompts can be confidently misclassified; there is no unknown detector.

No live inference, model download, new experiment runner or tokenizer is included.
Question instructions, choices, formatting and prompt share the model input
budget. This version forwards the prompt unchanged and does not count tokens,
guard overflow or verify SDK truncation. The long-string test proves transport
only. No safe character/line budget or complete-input processing is claimed.
See the [token-budget investigation handoff](https://chatgpt.com/library?file_id=libfile_34e77d9a23788191893a8542d585ea94&account_id=personal)
and [implementation plan](../../../../../docs/requested-action/requested-action-block-plan.md).

Future opt-in evaluation on Sharon's Mac should record model/revision, SDK version,
requested temperature, actual question/rule, raw and enriched output, expected
label/status, decision reason, and verified length/truncation diagnostics. Report
wrong accepted answers and abstentions separately; abstention is not a correct
classification. Distinguish requested model identity from verified loaded identity.
