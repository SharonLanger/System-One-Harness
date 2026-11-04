# Method Selection V2 · research and adoption decision

> **Selected: Q0 · combined-strict · temperature 0.5.** 65 correct selections, one incorrect selection, and 19 missed valid targets. Observed selection precision: **98.5%**. This is a development-set adoption decision; held-out validation remains pending.

## Why this profile

Method Selection V2 decides which single method to add to an explanation request. A missed selection gives up an enrichment opportunity; an incorrect selection can add irrelevant context. This experiment measures selection correctness, not downstream Claude answer quality or token savings.

The selected profile occupies the middle of the observed tradeoff: compared with ungated Q0, it avoids one incorrect selection while giving up eight correct selections. Compared with the strongest zero-error profile, it finds two additional correct targets but makes one incorrect selection. It is a deliberate tradeoff, not the highest overall-accuracy configuration.

## Five configurations worth comparing

These are a **decision shortlist**, not the first five rows sorted by accuracy: three distinct error/coverage tradeoffs, an aggregate tie for highest accuracy, and the previous baseline. Otherwise four temperature variants of ungated Q0 would consume most of the table. Exact accuracy leaders and all 80 vectors are provided below.

| Profile | Question | Rule | Temp. | Correct picks | Wrong picks | Missed targets / 84 | Pick precision | Overall / 120 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | Q0 | r1-ungated | 1.0 | 73 | 2 | 11 (13.1%) | 97.3% | 107 (89.2%) |
| B | Q0 | r7-entropy-075 | 0.5 | 73 | 2 | 11 (13.1%) | 97.3% | 107 (89.2%) |
| C **SELECTED** | Q0 | r9-combined-strict | 0.5 | 65 | 1 | 19 (22.6%) | 98.5% | 100 (83.3%) |
| D | Q1 | r5-gap-030 | 1.0 | 63 | 0 | 21 (25.0%) | 100.0% | 99 (82.5%) |
| E | Q0 | r0-current | 1.0 | 63 | 1 | 21 (25.0%) | 98.4% | 98 (81.7%) |

**Read the percentages correctly.** Miss rate = missed selections / 84 inputs with a single valid target. Pick precision = correct selections / all selections actually made. Wrong-pick rate is the complement of precision. Overall correctness = (correct selection + correct refusal) / all 120 inputs. A correct refusal is success; a missed target is not. These denominators differ deliberately.

For selected profile C: 66 selections = 65 correct + one incorrect; 54 refusals = 35 correct + 19 missed targets. Wrong-pick rate is **1/66 = 1.5%**. Selection yield is **65/84 = 77.4%**. Overall correctness is **100/120 = 83.3%**.

## Noise-level comparison — the same five configurations

The source labels are `regular`, `noisy`, and `heavy`; they are not a calibrated low/medium/high scale. Regular has 96 inputs (78 selectable, 18 requiring refusal); noisy has 18 (6 selectable, 12 requiring refusal); heavy has 6 (all requiring refusal). Reported precision can look excellent when few selections are attempted.

### Regular inputs

| Profile | Correct picks | Wrong picks | Missed targets | Pick precision | Correct refusals | Overall |
| --- | --- | --- | --- | --- | --- | --- |
| A | 67 | 2 | 11/78 (14.1%) | 97.1% | 16/18 | 83/96 (86.5%) |
| B | 67 | 2 | 11/78 (14.1%) | 97.1% | 16/18 | 83/96 (86.5%) |
| C | 60 | 1 | 18/78 (23.1%) | 98.4% | 17/18 | 77/96 (80.2%) |
| D | 58 | 0 | 20/78 (25.6%) | 100.0% | 18/18 | 76/96 (79.2%) |
| E | 58 | 1 | 20/78 (25.6%) | 98.3% | 17/18 | 75/96 (78.1%) |

### Noisy inputs

| Profile | Correct picks | Wrong picks | Missed targets | Pick precision | Correct refusals | Overall |
| --- | --- | --- | --- | --- | --- | --- |
| A | 6 | 0 | 0/6 (0.0%) | 100.0% | 12/12 | 18/18 (100.0%) |
| B | 6 | 0 | 0/6 (0.0%) | 100.0% | 12/12 | 18/18 (100.0%) |
| C | 5 | 0 | 1/6 (16.7%) | 100.0% | 12/12 | 17/18 (94.4%) |
| D | 5 | 0 | 1/6 (16.7%) | 100.0% | 12/12 | 17/18 (94.4%) |
| E | 5 | 0 | 1/6 (16.7%) | 100.0% | 12/12 | 17/18 (94.4%) |

### Heavy inputs

| Profile | Correct picks | Wrong picks | Missed targets | Pick precision | Correct refusals | Overall |
| --- | --- | --- | --- | --- | --- | --- |
| A | 0 | 0 | — (no valid targets) | — | 6/6 | 6/6 (100.0%) |
| B | 0 | 0 | — (no valid targets) | — | 6/6 | 6/6 (100.0%) |
| C | 0 | 0 | — (no valid targets) | — | 6/6 | 6/6 (100.0%) |
| D | 0 | 0 | — (no valid targets) | — | 6/6 | 6/6 (100.0%) |
| E | 0 | 0 | — (no valid targets) | — | 6/6 | 6/6 (100.0%) |

Heavy-noise success demonstrates refusal on these six inputs only. It supplies **no evidence about selecting a valid method under heavy noise**. Noisy selectable cases number only six; differences of one case are large percentage swings.

## Difficulty comparison

Each cell is correct selections / valid targets, followed by yield. All remaining outcomes in these four categories are missed selections: none of these five profiles chose a wrong candidate when a single valid target existed.

| Request type | A | B | C | D | E |
| --- | --- | --- | --- | --- | --- |
| Explicit method name | 28/30 (93.3%) | 28/30 (93.3%) | 27/30 (90.0%) | 27/30 (90.0%) | 26/30 (86.7%) |
| Description by meaning | 20/24 (83.3%) | 20/24 (83.3%) | 18/24 (75.0%) | 18/24 (75.0%) | 17/24 (70.8%) |
| Distracting method mentions | 16/18 (88.9%) | 16/18 (88.9%) | 13/18 (72.2%) | 11/18 (61.1%) | 13/18 (72.2%) |
| Same-name candidates | 9/12 (75.0%) | 9/12 (75.0%) | 7/12 (58.3%) | 7/12 (58.3%) | 7/12 (58.3%) |

Same-name candidates and distracting mentions expose the main loss in usefulness as acceptance becomes stricter. Difficulty and noise are separate breakdowns of the same inputs; do not add the tables together.

### Candidate-list size

| Candidate methods | A | B | C | D | E |
| --- | --- | --- | --- | --- | --- |
| 2 | 18/22 (81.8%) | 18/22 (81.8%) | 18/22 (81.8%) | 17/22 (77.3%) | 18/22 (81.8%) |
| 4 | 15/18 (83.3%) | 15/18 (83.3%) | 15/18 (83.3%) | 15/18 (83.3%) | 15/18 (83.3%) |
| 8 | 20/22 (90.9%) | 20/22 (90.9%) | 19/22 (86.4%) | 19/22 (86.4%) | 19/22 (86.4%) |
| 16 | 20/22 (90.9%) | 20/22 (90.9%) | 13/22 (59.1%) | 12/22 (54.5%) | 11/22 (50.0%) |

The groups differ in composition; this is descriptive evidence, not an isolated causal test of list size.

### When selection should be refused

| Situation — correct refusals | A | B | C | D | E |
| --- | --- | --- | --- | --- | --- |
| absent | 10/12 | 10/12 | 11/12 | 12/12 | 11/12 |
| ambiguous | 12/12 | 12/12 | 12/12 | 12/12 | 12/12 |
| multiple | 12/12 | 12/12 | 12/12 | 12/12 | 12/12 |

The selected profile's single incorrect selection occurs in the absent-target category. It correctly refuses every ambiguous and multiple-target input in this sample. Zero observed mistakes in profile D is not a guarantee of error-free operation.

## Exact questions and acceptance rules

**Q0 — selected wording**

> Select exactly one callable that the request asks to explain. Choose none_or_unclear when no single callable is appropriate.

**Q1 — alternative tested wording**

> Which single listed callable does the user want explained? Use the request and the callable names and signatures. Ignore callables mentioned only as background or explicitly excluded. Choose none_or_unclear if the target is absent, cannot be distinguished, or the request asks to explain multiple callables.

Both use dynamic readable method names/signatures and the sentinel description `No single matching callable, or unclear request.` No method bodies are supplied.

| Profile | Method acceptance condition |
| --- | --- |
| A — ungated | No method-confidence gate |
| B — entropy | normalized_entropy ≤ 0.75 |
| **C — selected combined-strict** | **answer_confidence ≥ 0.70 AND probability_gap ≥ 0.25** |
| D — gap-only | probability_gap ≥ 0.30 |
| E — previous baseline | answer_confidence ≥ 0.50 AND probability_gap ≥ 0.15 |

Confidence and gap are model scores, not measured probabilities that the selection is correct. “Combined” in combined-strict means **two acceptance conditions**, not combining Q0 and Q1. A gap of 0.25 requires the top option's probability to exceed the runner-up by at least 0.25.

**Fixed guard in every tested profile**

> Does the request require explaining more than one candidate callable?

This guard requires answer_confidence ≥ 0.50 and an accepted `no` before a method is selected. A sentinel method answer, rejected method decision, undecided guard, or `yes` guard returns no selection. Ungated disables only the method gate. Both questions are sent in one model request; Q0 and Q1 are alternatives and are never blended.

The V2 adoption preserves this guard because removing it would create an untested profile. Block-default temperature becomes **0.5**; an explicitly supplied runtime temperature still overrides it. The experiment adapter continues to supply its own questions, rules and temperature. The method question already matched Q0 before this change; the adoption pins V2's own catalog entries, rather than inventing new wording.

## What was measured

| Dimension | Experiment scope |
| --- | --- |
| Campaign | method-selection-200, dataset version 1 |
| Reported run | 2026-11-01_00-24-49 |
| Frozen dataset | 200 inputs; 100 semantic families |
| Analyzed split | **Development only: 120 inputs, 84 selectable + 36 refusal** |
| Reserved split | 80 held-out inputs; not analyzed here |
| Sweep | 2 question wordings × 10 rules × 4 temperatures = 80 vectors |
| Temperatures | 0.5, 0.8, 1.0, 1.1 |
| Development predictions | 960 unique predictions; rules replayed into 9,600 outcomes |
| Completion | All 80 vectors complete; no errors, timeouts, skips or unattempted cases |
| Suite model setting | aac6fef/laya-typed-decisions-mlx; English |
| Review | Author self-review; independent semantic review outstanding |

The model string above is the frozen suite setting, not an independently verified runtime/model revision. Downloaded aggregate exports do not establish installed package version, hardware, exact model revision or truncation behavior. No live inference was rerun for this report.

## Temperature and ranking

Q0 ungated has identical aggregate outcomes at all four temperatures: 73 correct selections, 2 incorrect selections, 11 missed targets and 34 correct refusals. This does not establish identical per-case answers or that temperature has no effect. Gated profiles change with temperature.

The literal top five by overall correctness are tied at 107/120 (89.2%):

| Question | Rule | Temperature | Correct picks | Wrong picks | Missed |
| --- | --- | --- | --- | --- | --- |
| q0-baseline | r1-ungated | 0.5 | 73 | 2 | 11 |
| q0-baseline | r1-ungated | 0.8 | 73 | 2 | 11 |
| q0-baseline | r1-ungated | 1.0 | 73 | 2 | 11 |
| q0-baseline | r1-ungated | 1.1 | 73 | 2 | 11 |
| q0-baseline | r7-entropy-075 | 0.5 | 73 | 2 | 11 |

The selected C profile is on the observed tradeoff frontier: no tested configuration selects more correct targets while making at most one incorrect selection. A/B lead at two errors; D leads at zero errors. E is included for continuity, not as a frontier winner. Profile B's aggregate tie with A does not prove identical per-case behavior.

## Interpretation and next validation

- **Adopted preference:** C balances enrichment opportunity and misleading context, as chosen by Sharon. It is a selection based on this development sample, not statistical proof of superiority.
- **Main weakness:** distinguishing same-name methods and retaining valid targets as candidate lists grow. Refusal is a lost opportunity; the consuming flow determines fallback behavior.
- **Limits:** synthetic explanation requests, one run per question/temperature, related examples within semantic families, small subgroup denominators, and no independent annotation review. Do not generalize to edit/fix/test intents or production traffic without evaluation.
- **Next checkpoint:** freeze C and one comparator using the campaign's finalists schema, then evaluate the reserved 80 cases. Do not tune on held-out results. Separately check downstream context usefulness with the real flow.
- **No accuracy claim from pooled totals:** the 9,600 outcomes repeat the same 120 inputs under competing policies. They are not 9,600 independent requests and are not an ensemble.

## Implementation verification

The adoption is covered by **311 passing offline tests**, including **13 new profile tests**. Checks cover exact suite question/rule parity; both strict threshold boundaries; fixed-guard acceptance and refusal; actual model-loader temperature; caller-config immutability; explicit overrides; experiment adapter settings; first-flow integration; and wheel packaging. No live model experiment was run for this change.

All 80 vectors' totals reconcile with each of their noise, difficulty and candidate-count breakdowns. Committed evidence files have SHA-256 checksums in the source manifest. Plugin runtime behavior is released as hook-laya **1.3.0**.

## Research sources and reproducibility

All numbers above derive from the downloaded development exports committed beside this report. The source manifest records their Drive locations and SHA-256 checksums. `raw-answers.csv` is an aggregate answer summary, not per-input raw model evidence.

- Vectors — all 80 configurations (historical material; see docs/cleanup-local-files.md)
- Group results — all noise, difficulty and candidate-count breakdowns (historical material; see docs/cleanup-local-files.md)
- Raw-answer aggregate summary (historical material; see docs/cleanup-local-files.md), totals (historical material; see docs/cleanup-local-files.md), decision reasons (historical material; see docs/cleanup-local-files.md), baseline differences (historical material; see docs/cleanup-local-files.md)
- Evidence provenance and checksums (historical material; see docs/cleanup-local-files.md)
- [Original development folder](https://drive.google.com/drive/folders/1lSb1YXL5VRbGqkoAgOVoNUBuP5pXCJqY)
- [Original experiment summary](https://drive.google.com/file/d/1hHjUISHT4Xa0vSXGfUOD0vcpYTTTadYw/view)
- [Experiment design and execution guide](../../../../../../experiments/batch_v2/docs/campaigns/method-selection-200/README.md)
- [Expanded experiment plan](../../../../../../experiments/batch_v2/docs/campaigns/method-selection-200/plan.md)
- [Dataset design](../../../../../../experiments/batch_v2/docs/campaigns/method-selection-200/dataset-summary.md) and [annotation review](../../../../../../experiments/batch_v2/docs/campaigns/method-selection-200/annotation-review.md)
- [Frozen suite: exact questions, rules, model and temperatures](../../../../../../experiments/batch_v2/experiments/method-selection-200/rounds/001-small/suite.json)
- [Original ten-rule source: requested-action-500 v1](../../../../../../experiments/batch_v2/experiments/requested-action-500/versions/1/suite.json)

Cases hash recorded in reports: `430bcd38555e41949fd6e8023461e23870876bed26e6304c4e79cc8e622db939`.

Suite hash recorded in reports: `008081ab463f2487c6a2a231b1997729f1830e018d73ed9137d0f1c2b6a7837f`.
