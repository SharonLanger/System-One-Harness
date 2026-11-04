# Requested-action 500 V2: five-combination comparison and selected default

## Decision

Sharon selected **combination #3**: **C1 short choices**, requested **temperature 1.0**, and **R4 probability gap ≥ 0.10**. The combination numbers below are stable identifiers from the easy-case shortlist; they are not a new ranking of overall performance.

On the 66 simple cases, #3 accepted **51 answers, all correct** (77.3% answer rate). Across all 500 cases, it accepted **286 answers: 211 correct and 75 wrong** (57.2% answer rate; **26.2% wrong among accepted**). It rejected the remaining 214 cases. This selection is a user-chosen coverage/error trade-off, **not evidence that the overall 10–20% failure target has been achieved**. The 21.0% overall wrong rate belongs to #4, not #3.

## Research scope and source

This report records the exact five-combination results discussed with Sharon. It analyzes the existing uploaded summary; it does not rerun inference, alter the frozen campaign, or claim a new live validation. All 500 cases are used for this retrospective comparison.

- Source: [uploaded summary.csv](https://drive.google.com/file/d/1lM9PM1eb97IdYvTh3c6KiII8IKtxq_OD/view).
- Original file size: 11884544 bytes.
- SHA-256: `4d15234e754239670741bceb5495f35af3e373363b0b8040c1acf191aceb3115`.
- [Exact five-combination aggregate evidence](data/requested-action-500-top-five.csv) is included with this report, retaining the original field values and confusion tables for each displayed group.
- Code/design reference inspected: `01e15612ba41adbc075a13b7161b2ef00108afbe`. This is the inspected repository revision, not a verified source revision of the uploaded run: the CSV does not embed its run ID, manifest, SDK version, or code fingerprint.

### Design documents

- Requested-action building-block design (historical material; see docs/cleanup-local-files.md).
- [500-case campaign overview](../../experiments/batch_v2/docs/campaigns/requested-action-500/README.md).
- [Task definition and label meaning](../../experiments/batch_v2/docs/campaigns/requested-action-500/task-definition.md).
- [Dataset summary](../../experiments/batch_v2/docs/campaigns/requested-action-500/dataset-summary.md).
- [V2 unclear-label migration](../../experiments/batch_v2/docs/campaigns/requested-action-500/unclear-v2.md).
- [Round 001 design, variants, rules and temperatures](../../experiments/batch_v2/docs/campaigns/requested-action-500/rounds/001-broad.md).
- [Frozen executable suite](../../experiments/batch_v2/experiments/requested-action-500/rounds/001-broad/suite.json).
- [Summary metric implementation](../../experiments/batch_v2/reporting.py).
- [Building-block usage and current contract](../../src/laya_context_router/building_blocks/questions/requested_action/README.md).

### What the campaign measured

The classifier chooses one of `explain`, `generate_tests`, `modify_code`, and `unclear`. A separate rule accepts or rejects the prediction. There are 500 synthetic inputs from 125 scenario families, with four variants per family. The grid combines 10 question/choice variants and seven requested temperature settings, giving 35,000 prediction slots. Each saved prediction is evaluated by ten rules, giving 350,000 rule outcomes. The CSV reports all planned outcomes completed, with no errors, timeouts, skipped cases or unattempted cases. This describes the export; the run manifest was not supplied to independently verify execution provenance.

The original split was 200 development cases, 100 temperature-calibration cases, 100 policy-calibration cases, and 100 held-out cases. Here, all 500 are included at Sharon’s request. Because those outcomes inform this selection, the original held-out cases are not an untouched confirmation set for the selected profile.

## How to read the results

- **Answer rate / coverage:** `(AC + AW) / cases`.
- **Wrong rate:** `AW / (AC + AW)`, the fraction of accepted classifications that are wrong.
- **AC:** accepted correct; **AW:** accepted wrong; **RC:** rejected correct; **RW:** rejected wrong.
- Rejections are fallbacks, not accepted mistakes. A wrong raw prediction that is rejected is filtered out.
- Accepted `unclear` counts as an accepted classification in these metrics, but it is non-actionable for enrichment. The aggregate CSV does not separate accepted labels, so actionable-output coverage/error cannot be reconstructed from these tables.
- No accepted answers means undefined wrong rate, displayed as **—**, not 0%.
- Percentages are computed from integer counts and rounded to one decimal. Only one group is used at a time; overlapping group rows are never added together.
- The probability gap is the highest minus the second-highest class probability. Runtime enrichment rounds it to four decimals before the inclusive comparison; this report preserves that existing R4 behavior.

## The five selected combinations

We first ranked the easy subset by zero observed accepted errors, then highest answer rate. All **66 cases tagged `simple` have noise level `regular`**. The following five had the highest answer counts among zero-error combinations. Zero observed mistakes is a result on this sample, not a guarantee of future accuracy.

| # | Question | Temperature | Rule | Answered | Answer rate | Wrong among accepted |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | C2 explicit choices | 0.5 | R8: confidence ≥ 0.45 AND gap ≥ 0.10 | 53 | 80.3% | 0.0% (0/53) |
| 2 | C1 short choices | 0.5 | R0: confidence ≥ 0.50 AND gap ≥ 0.15 | 51 | 77.3% | 0.0% (0/51) |
| **3** | C1 short choices | 1.0 | R4: gap ≥ 0.10 | 51 | 77.3% | 0.0% (0/51) |
| 4 | C1 short choices | 0.5 | R5: gap ≥ 0.30 | 50 | 75.8% | 0.0% (0/50) |
| 5 | C2 explicit choices | 1.0 | R4: gap ≥ 0.10 | 48 | 72.7% | 0.0% (0/48) |

For comparison, C1 / temperature 0.5 / R8 accepted 54 easy cases with one error (81.8% answer rate; 1.9% wrong among accepted). It added one answer but no additional correct answer relative to #1. It is outside the five-combination shortlist and is not the selected default.

## Overall results: all 500 cases

| # | Question | Temperature | Rule | Answered | Answer rate | Wrong among accepted |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | C2 explicit choices | 0.5 | R8: confidence ≥ 0.45 AND gap ≥ 0.10 | 376 | 75.2% | 32.2% (121/376) |
| 2 | C1 short choices | 0.5 | R0: confidence ≥ 0.50 AND gap ≥ 0.15 | 297 | 59.4% | 28.3% (84/297) |
| **3** | C1 short choices | 1.0 | R4: gap ≥ 0.10 | 286 | 57.2% | 26.2% (75/286) |
| 4 | C1 short choices | 0.5 | R5: gap ≥ 0.30 | 238 | 47.6% | 21.0% (50/238) |
| 5 | C2 explicit choices | 1.0 | R4: gap ≥ 0.10 | 313 | 62.6% | 28.1% (88/313) |

**#1 provides the broadest coverage. #4 has the lowest overall wrong rate. #3 is the selected middle-ground profile, with lower overall error than #1, #2 and #5 but higher error than #4.**

## Results by noise level

Each cell below is **answer rate / wrong rate**, both in percent. These three groups partition the dataset. “Regular” means readable text, not easy intent: it includes misleading/background variants.

| Input group | Cases | #1 | #2 | #3 | #4 | #5 |
| --- | --- | --- | --- | --- | --- | --- |
| Regular | 250 | 75.2 / 29.3 | 63.6 / 27.7 | 59.2 / 24.3 | 50.8 / 18.9 | 64.0 / 23.8 |
| Noisy | 125 | 80.8 / 16.8 | 68.0 / 11.8 | 65.6 / 9.8 | 57.6 / 5.6 | 68.8 / 15.1 |
| Heavy noise | 125 | 69.6 / 56.3 | 42.4 / 56.6 | 44.8 / 55.4 | 31.2 / 56.4 | 53.6 / 55.2 |

All five have approximately 55–57% wrong among accepted heavy-noise answers. The lower wrong rates in the noisy group do not establish that adding typos improves classification: the noise groups also differ in prompt construction and background challenges.

## Results by challenge type

Each cell is **answer rate / wrong rate**, both in percent. Tags overlap and must not be summed. `irrelevant-text` and `misleading` have identical aggregate values here; both are shown using their original labels. Very small groups, especially review disagreement (two cases), cannot establish stable performance.

| Input group | Cases | #1 | #2 | #3 | #4 | #5 |
| --- | --- | --- | --- | --- | --- | --- |
| Simple / easy | 66 | 80.3 / 0.0 | 77.3 / 0.0 | 77.3 / 0.0 | 75.8 / 0.0 | 72.7 / 0.0 |
| Boundary cases | 136 | 75.0 / 48.0 | 55.9 / 53.9 | 49.3 / 50.7 | 36.8 / 44.0 | 60.3 / 43.9 |
| Irrelevant text | 250 | 69.2 / 51.4 | 48.4 / 51.2 | 48.4 / 50.4 | 35.6 / 49.4 | 54.4 / 47.1 |
| Misleading text | 250 | 69.2 / 51.4 | 48.4 / 51.2 | 48.4 / 50.4 | 35.6 / 49.4 | 54.4 / 47.1 |
| Missing context | 20 | 80.0 / 100.0 | 30.0 / 83.3 | 25.0 / 80.0 | 20.0 / 100.0 | 60.0 / 100.0 |
| Mixed intent | 50 | 72.0 / 97.2 | 62.0 / 100.0 | 50.0 / 100.0 | 34.0 / 100.0 | 62.0 / 96.8 |
| Negation | 192 | 74.0 / 42.3 | 50.5 / 37.1 | 51.6 / 35.4 | 39.1 / 32.0 | 58.9 / 38.9 |
| Typos | 250 | 75.2 / 35.1 | 55.2 / 29.0 | 55.2 / 28.3 | 44.4 / 23.4 | 61.2 / 32.7 |
| Reviewer-challenging | 16 | 87.5 / 64.3 | 37.5 / 83.3 | 37.5 / 83.3 | 31.2 / 100.0 | 68.8 / 54.5 |
| Review disagreement | 2 | 100.0 / 0.0 | 100.0 / 0.0 | 100.0 / 0.0 | 100.0 / 0.0 | 0.0 / — |
| Untagged | 12 | 75.0 / 22.2 | 75.0 / 33.3 | 75.0 / 33.3 | 50.0 / 0.0 | 66.7 / 12.5 |

## Interpretation

1. **Easy requests are the strongest observed use case.** Every shortlisted combination has zero accepted mistakes on the simple subset; #1 answers the most, and #3 answers 51/66.
2. **#3 retains useful coverage on noisy inputs.** It answers 82/125 noisy cases, with eight mistakes: 65.6% answer rate and 9.8% wrong among accepted.
3. **Readable does not mean unambiguous.** On regular inputs, #3 answers 148/250 with 36 mistakes: 59.2% answer rate and 24.3% wrong.
4. **Heavy noise remains a failure mode.** #3 answers 56/125 heavy-noise cases with 31 mistakes: 44.8% answer rate and 55.4% wrong.
5. **Mixed intent and missing context are especially weak.** #3 accepts 25 mixed-intent cases and all 25 are wrong; it accepts five missing-context cases and four are wrong. The gap rule is not a reliable ambiguity detector on these cases.
6. **A stricter rule trades useful answers for fewer overall mistakes.** #4 accepts 238/500 with 50 wrong (21.0%), compared with #3’s 286/500 and 75 wrong (26.2%). Neither meets a below-20% overall error requirement on this dataset.
7. **No ensemble result is established.** Aggregate tables do not show whether the five agree on the same individual prompts or share the same mistakes.

## Selected implementation

### Exact question

The default question is copied exactly from `c1-short-choices` in the V2 suite, including all four ordered choices and the shared instruction. The raw choice IDs remain `explain`, `generate_tests`, `modify_code`, `unclear`.

```json
{
  "name": "requested_action",
  "type": "choice",
  "instructions": "What work does the user request: explain existing code, generate tests, or modify code? Classify the requested outcome, not the files that must be read. Adding test coverage belongs to generate_tests; repairing existing code, including tests, belongs to modify_code. An explanation alone does not request edits. Choose unclear if none of these actions fits, the requested action cannot be determined, or competing actions prevent selecting one primary action. Do not invent precedence between code changes and additional tests when both are requested as deliverables. Explanation supporting a clear edit or new-test deliverable does not make it unclear. Missing source code alone does not make an otherwise clear requested action unclear.",
  "criteria": {
    "explain": "Explain production or test code; no edits.",
    "generate_tests": "Add new tests / additional coverage.",
    "modify_code": "Fix, refactor or implement code, including existing-test repair.",
    "unclear": "Cannot select one supported action: missing intent, competing actions, or none fits. Non-actionable."
  }
}
```

### Rule and temperature

- The runtime name stays `requested_action_default`; its single condition matches experimental R4: `probability_gap >= 0.10`. There is no answer-confidence or entropy gate.
- This block uses requested temperature **1.0** when the caller’s `RunConfig.temperature` is `None`. Explicit numeric overrides, including 0, are preserved.
- The caller’s immutable config, selected model, language, shared runtime and other blocks are not changed. The caller-owned registry caches the resulting model/temperature/language key as before. A flow using SDK defaults in a later block may load a separate cached agent because its temperature differs.
- Accepted `unclear` remains visible as `answer="unclear", decided=True` in detailed decisions, but the public block result is `{"action":"undecided"}`. Rule rejection also returns that public fallback and remains distinct in decisions (`decided=False`).
- The public action outputs remain the existing three actions plus `undecided`, so the current first-method-context flow follows its existing no-enrichment path for unclear requests.
- Question overrides must now preserve the four V2 choice IDs. Historical three-choice overrides and synthetic responses need the fourth choice; this is an intentional question-contract migration.
- The Python package advances from 0.1.0 to 0.2.0. The plugin release advances from 1.1.0 to 1.2.0 and documents the changed requested-action runtime behavior. The frozen experiment suite and datasets are not rewritten.

## Verification and limits

Profile tests pin the production question and rule to the frozen C1/R4 definitions; check the inclusive gap boundary, four-choice response handling, unclear fallback, explicit temperature overrides, caller-config immutability, and agent reuse. Existing block, override, logging, resource-packaging and flow tests are run with synthetic responses. These checks verify implementation behavior, not new model accuracy. No live model calls or new 35,000-call experiment are required for this change.

This report is a retrospective result on 125 related synthetic scenario families, not 500 independent production requests. Selection used the reported outcomes. The source CSV does not provide per-case predictions/probabilities, family-paired uncertainty, or accepted-label breakdowns. A fresh realistic evaluation is needed to measure deployment accuracy and actionable enrichment error; the current selected combination is not represented as satisfying the original overall 10–20% error target.
