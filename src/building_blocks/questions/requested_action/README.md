# Requested action

Classify the requested outcome from one prompt using the shared V2 runtime.
The opt-in `first_method_context` flow calls this block before selecting methods.

## Selected profile and research

The default is combination **#3** from the
[500-case V2 research report](../../../../../docs/requested-action/requested-action-500-results.md):

- **Question:** C1 short choices, with four ordered labels.
- **Requested temperature:** 1.0 when the caller leaves temperature unset.
- **Rule:** R4, `probability_gap >= 0.10` (inclusive), with no confidence gate.

On the 66 easy cases, this combination accepted 51 answers with zero observed
mistakes. On all 500 cases, it accepted 286 answers with 75 mistakes: **57.2%
coverage and 26.2% wrong among accepted answers**. The easy-case result is not an
accuracy guarantee or evidence of a below-20% overall failure rate. The report
contains all five compared profiles, exact tables, source evidence, design links,
and the decision to adopt #3.

```python
from building_blocks.questions.requested_action.block import run
from laya.config import RunConfig
from laya.registry import AgentRegistry

# The caller owns the invocation's registry. Inject a loader in tests.
# real=True is only for deliberate live execution.
registry = AgentRegistry(real=True)
result = run({"prompt": "Write tests for calculateTotal in invoice.ts."},
             config=RunConfig(), registry=registry)
# Uses requested temperature 1.0 for this block.
# result.data == {"action": "generate_tests"} if that label is accepted.
```

## Input and choices

Input is exactly `{"prompt": nonblank_string}`. Missing/extra keys and nonstring
or blank values raise BlockInputError before agent loading. The original text,
including surrounding whitespace, Unicode and filenames, passes unchanged.
Filenames are text; this block reads no target files or TypeScript outlines.

The question lives in `defaults/questions/requested_action.json`; `block.json`
references it. It exactly matches the campaign's C1 definition, including the
shared instruction and these four choice descriptions:

| Choice | Description |
| --- | --- |
| `explain` | Explain production or test code; no edits. |
| `generate_tests` | Add new tests / additional coverage. |
| `modify_code` | Fix, refactor or implement code, including existing-test repair. |
| `unclear` | Cannot select one supported action: missing intent, competing actions, or none fits. Non-actionable. |

The separate typed rule `requested_action_default` applies only the enriched
probability gap. Enrichment subtracts the second-highest probability from the
highest and rounds to four decimals before the inclusive 0.10 comparison.
`answer_confidence`, SDK confidence and `act_probability` are not acceptance gates.
Malformed supplied confidence fields still fail ordinary response validation.

## Output and fallback

Returns the existing BlockResult. Successful evaluation has status `completed`,
null top-level reason, and one detailed decision.

| Prediction outcome | Detailed decision | Public `data.action` |
| --- | --- | --- |
| Accepted supported action | Original action, `decided=True` | `explain`, `generate_tests`, or `modify_code` |
| Accepted `unclear` | `answer="unclear"`, `decided=True` | `undecided` |
| Rule rejection | `answer="undecided"`, `decided=False`, evaluator reason | `undecided` |

The public result remains exactly `{"action": <action>}`. Accepted unclear and rule
rejection are distinguishable in detailed decisions, but both take the existing
no-enrichment path in `first_method_context`. There is no new public action branch.
Intent classification does not authorize edits or establish the edit target.

A caller's SkipBlock yields status `skipped`, its top-level reason, empty decisions,
and `{"action": "undecided"}`. Invalid input/configuration and malformed SDK
responses are errors. Loader errors, SDK exceptions and TimeoutError propagate;
there is no retry, fallback model or fabricated classification.

## Configuration and overrides

The wrapper replaces an unset (`None`) temperature with **1.0** for this block
only. It preserves explicit numeric temperatures (including 0), model, language,
and the caller's immutable RunConfig. Shared RunConfig defaults and other blocks
are unchanged. Default and explicit 1.0 calls reuse the same registry entry.
A later block using SDK-default temperature can load a separate cached agent.
Calling the generic `Block` runtime directly bypasses this wrapper's default;
use this module's `run` function for the selected profile.

```python
result = run(
    {"prompt": prompt}, config=RunConfig(temperature=0.5), registry=registry,
    rule_overrides={"requested_action": "my_choice_rule"},
    question_overrides={"requested_action": full_choice_question},
    catalog=my_catalog,
)
```

Named rules must exist in the supplied catalog and be choice-compatible. Question
overrides may be a full definition or catalog reference. Instructions,
descriptions and order can change, but overrides must retain type `choice` and
all **four** IDs. Historical three-choice overrides/responses must add `unclear`.
A full definition contains `type`, `instructions`, and `criteria`. There is no
inline rule merge. Caller inputs and catalog defaults are not mutated.

Custom `prepare_input(value, questions)` can explicitly replace submitted text
and return PreparedInput. Text must stay nonblank, and question names, type and
labels must remain valid. Custom state does not determine the result.
Construction/catalog access does not load a model. Each run uses one prediction
and one enrichment; the caller owns registry lifetime. Debug logs retain the
resolved configuration, question, raw response, enriched metrics and decision.

## Evaluation and input limits

Run deterministic tests with `python -m pytest -q tests/test_requested_action*.py`.
These use synthetic SDK responses and verify transport, validation, extraction,
configuration, gap boundaries, unclear fallback and exact parity with the frozen
C1/R4 experiment definitions. They do not measure live semantic accuracy.

The older E01–E22 corpus in `tests/fixtures/requested_action_prompts.json` retains
its historical annotations; it is not the V2 500-case evidence. The research report
links the current campaign and explains its four-label taxonomy and limitations.

No model download or live inference is needed to test these changes. Question
instructions, choices, formatting and prompt share the model input budget. This
block forwards the prompt unchanged and does not itself count tokens, guard
overflow or verify SDK truncation. Long-string tests prove transport only.
See the [token-budget implementation plan](https://chatgpt.com/library?file_id=libfile_1ac2aa7c68b8819195ce55d60dc35792&account_id=personal)
and [original block design](../../../../../docs/requested-action/requested-action-block-plan.md).
