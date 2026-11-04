# Method selection V2

## Research documentation and selected profile

**Method-selection-200 defines the V2 default: Q0 + combined-strict at temperature 0.5.** The method answer must satisfy confidence ≥ 0.70 **and** probability gap ≥ 0.25. The fixed multiple-method guard remains part of the tested decision. Q0 and Q1 are alternative experiment wordings, not a combined question.

On the 120-input development split, this profile selected **65 correct methods and one incorrect method**, missed **19/84 valid targets (22.6%)**, and correctly refused **35/36** no-single-target requests. Observed pick precision was **98.5%**; overall correctness including refusals was **83.3%**. Held-out validation is pending.

| Profile | Question | Rule | Temp. | Correct picks | Wrong picks | Missed targets / 84 | Pick precision | Overall / 120 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | Q0 | r1-ungated | 1.0 | 73 | 2 | 11 (13.1%) | 97.3% | 107 (89.2%) |
| B | Q0 | r7-entropy-075 | 0.5 | 73 | 2 | 11 (13.1%) | 97.3% | 107 (89.2%) |
| C **SELECTED** | Q0 | r9-combined-strict | 0.5 | 65 | 1 | 19 (22.6%) | 98.5% | 100 (83.3%) |
| D | Q1 | r5-gap-030 | 1.0 | 63 | 0 | 21 (25.0%) | 100.0% | 99 (82.5%) |
| E | Q0 | r0-current | 1.0 | 63 | 1 | 21 (25.0%) | 98.4% | 98 (81.7%) |

This is a five-profile decision shortlist, including the previous baseline; it is not a pure accuracy ranking. Missed percentages use 84 selectable inputs, precision uses actual selections, and overall correctness uses all 120 inputs.

**[Read the full research report →](research/method-selection-200-results.md)** for the same five profiles by noise level, harder request types and candidate count; exact question wording and rules; the accuracy leaders; limitations; and links to experiment design and original summaries. Downloadable evidence (historical material; see docs/cleanup-local-files.md) preserves provenance and all 80 configurations.

The block uses 0.5 when no temperature is supplied; explicit runtime overrides remain supported. The reported results apply to the exact selected settings. See the report before changing the guard or interpreting “ungated” as always selecting a method.

## Input and runtime contract

Supply `{"text": string, "source_outline": outline}` to `run`, together with
explicit `config` and `registry`. `source_outline` must be the full validated
TypeScript outline, including schema version, source identity, ranges,
locations, diagnostics and limitations. The block performs no filesystem reads.

```python
from building_blocks.typescript import outline, extract_callable
from building_blocks.questions.method_selection_v2.block import run
source = outline("/project/src/invoice.ts")  # deterministic utility
selection = run({"text": "Explain calculateTotal", "source_outline": source},
                config=config, registry=registry)  # one model request
if selection.status == "completed" and selection.data["selected_id"] is not None:
    code = extract_callable(source["path"], selection.data["selected_id"])
```

Readable names/signatures and `none_or_unclear` are sent to the model; opaque
source IDs remain in `data.candidate_map` and `data.label_map`. Selection requires
an accepted method answer and an accepted `multiple_relevant=no` answer.
Rejected decisions remain `completed` with a domain reason; expected no-work
conditions return `skipped`, a nonempty reason and empty decisions.

`max_candidates=64` and `max_input_chars=16000` retain existing counting rules:
prompt length plus compact JSON question length, measured in Unicode characters.
No source/prompt truncation occurs. Empty candidates, candidate overflow, repeated
signatures and character overflow skip prediction. Invalid outlines/limits raise.

`rule_overrides`, `question_overrides`, `prepare_input`, and `catalog` are explicit
per-call options. Custom preparation receives validated input and copied question
definitions and must return `PreparedInput(text, questions, state)`. Preserve
candidate and label maps in state; source identity and budgets are revalidated.
To read a file during preparation, use a thin adapter that calls `outline` before
passing this input contract. Original `method_selection.block.run(text, outline,
...)` remains the compatibility API returning its original dictionary shape.

The compatibility adapter is migrated for versioned compiler outlines. Older
unversioned abbreviated outlines continue through `method_selection.block.run_legacy`,
which remains callable explicitly for comparison or rollback. A present but invalid
`schema_version` raises through V2 validation; it never triggers legacy fallback.
Source identities are never synthesized to make an abbreviated outline look valid.
