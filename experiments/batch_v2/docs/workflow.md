# LAYA experiment workflow blueprint

Date: 2026-10-31
Status: actionable research protocol; no cases generated, code implemented or model results claimed by this document.

This is the reusable procedure for discovering a classification configuration before creating or changing a production building block. Start with a task contract and the generic-question adapter. The task-specific document defines the question and labels independently of any existing implementation. See [research notes](research-notes.md) for the rationale and [records and handoffs](records-and-handoffs.md) for run history.

Companions:
- [Implementation work plan](implementation-plan.md): tasks needed to execute this procedure.
- [Input-agent handoff](input-authoring.md): instructions for creating and reviewing the fixed cases.

## 1. Decisions already made

- One task and canonical label set per experiment.
- Same frozen case file, IDs, texts, labels and annotations throughout a campaign.
- Question variants preserve class meanings and choice order.
- Every selected question is crossed with every selected temperature/configuration in a round. Rules reuse predictions when replay is verified.
- Do not remove difficult cases after seeing failures. A necessary label correction starts a new dataset version and a new campaign.
- No production changes. New score functions remain isolated experiment modules until a later, evidence-backed promotion.
- Missing cases and helpers are assigned work, not unanswered questions for Sharon.
- No single deployment error target is required for research. Preserve several useful trade-offs.

PR #21 is merged into main at 83211fd88d10e4c0854797dec47df33ce8d04ea5. Its implementation was reviewed at 7a1b031191d81edc3d9ac1993a972b989e91c2e9. RV2 is implemented with fixed choice order, one evaluation per case/vector, and no repetitions field. A separate launch is a new run. This protocol adds no hidden repetitions or order permutations.

## 2. Scoring contract

Read [scoring.md](scoring.md) before selecting candidates. Label quality, probability calibration and rejection quality are separate objectives. Score settled cases only; report unsettled-case behavior separately. Current and planned report features are distinguished in [implementation-plan.md](implementation-plan.md).

## 3. Freeze the campaign before running

The experiment owner completes a task-specific experiment document with:
- Task contract and authored Q0 reference; canonical labels/order; generic-question adapter. An existing block's question can supply Q0 only when its meaning and submitted input match this task.
- Q1 concise wording, Q2 explicit boundaries, C1 shorter descriptions, C2 explicit descriptions. Review all five for equivalent meaning.
- Exact model/configuration and verified temperature interval.
- Dataset hash; source-family split map; critical subgroup list.
- Round rules below, engineering tolerances, allowed analysis roles and call/time budget.

No existing production block is required. For generic-question, input is the exact string LAYA receives. If a task needs structured context, freeze an explicit text-rendering contract before authoring cases; all variants use it. A later production block must reproduce that payload or be reevaluated.

The input-agent handoff supplies a concrete starting dataset specification. Keep development, temperature-calibration, policy-calibration and held-out roles fixed by source family. Existing RV2 split values remain development/calibration/held_out; a sidecar divides calibration families into temperature and policy roles.

All rounds can submit the same complete cases.json. The research analyzer must filter to permitted IDs before computing tuning metrics and must not load held-out predictions during selection. Existing RV2 overall reports include held-out outcomes: do not inspect those combined reports during tuning. A dedicated tuning report is an implementation task. The final report unlocks held-out results after finalists are frozen.

Synthetic benchmark calibration describes that benchmark's distribution. Do not present it as calibrated production traffic without representative evidence.

## 4. The round controller

The following pseudocode is the intended workflow, not an existing command:

```text
freeze(task_contract, cases, splits, critical_groups, settings)
preflight_runner_and_response_fields()
R0 = baseline_reference()
R1 = broad_matrix(all_question_variants, initial_temperatures)
questions = retain_baseline_and_unresolved_contenders(R1.development)

for refinement in 1..3:
    regions = temperature_regions(results.temperature_calibration, questions)
    if regions_are_stable_or_no_new_values: break
    next_temperatures = union(refine_each_region(regions))
    run_matrix(questions, next_temperatures, fixed_cases)

fit_or_select_temperature_candidates()
sweep_rule_thresholds(policy_calibration_only)
freeze_finalists_and_thresholds()
evaluate_held_out_once_for_selection_free_final_report()
```

Each round writes a decision record: evidence used, case-role hashes, retained/discarded candidates and reasons, next suite settings, unavailable metrics and stop/continue status. Decisions must be reproducible from saved records.

### R0 — baseline reference

Run Q0 at SDK default and explicit T=1 with the declared R0 reference rule and ungated output. R0 is a complete authored rule; if a compatible production rule exists, copy its definition as a reference. Its existence is not a prerequisite. Use the full frozen case file, but inspect only development and permitted calibration evidence.

Expect: valid labels/probabilities, clear technical statuses, current four-cell outcomes and a dataset-level majority baseline.

If a configuration fails technically, fix or mark it unavailable; never interpret failure as poor model quality. If labels change solely with positive scalar temperature, inspect ties, precision, settings or a changed runtime path before attributing an accuracy gain to calibration.

### R1 — broad matrix

Run all five question variants at SDK default plus explicit temperatures 0.5, 1, 1.5, 2, 3, 5, only after confirming support. These values are an engineering starting grid spanning the previously reviewed 0.5–5 interval, not a paper's recommended optimum. An unsupported value is excluded with a reason, never silently clamped.

Keep the declared R0 rule unchanged and retain the ungated reference. Analyze additional scalar scores offline on the same predictions; runtime threshold sweeps need not multiply model calls.

With 1,200 cases, five questions and seven configurations, verified rule replay needs 42,000 inference calls; two rules create 84,000 logical outcomes. Print actual counts and measured throughput; do not promise a duration. Offline temperature evaluation can reduce calls only through a verified route in [scoring.md](scoring.md).

Expected outputs:
- Development: label-quality and subgroup comparison.
- Temperature calibration: NLL versus temperature per question.
- No held-out ranking or threshold selection.

### R2 — retain questions and refine temperature

Always retain Q0. Retain the best development balanced-accuracy and MCC candidates, and candidates that improve a predeclared critical group or rule trade-off on development evidence. Do not pick wording from held-out outcomes.

Only prune a candidate when paired source-family comparisons show it is consistently worse with no critical-group benefit. Default practical tolerance: 0.02 absolute balanced-accuracy/MCC and 0.02 per-class recall; these are declared engineering choices. If confidence intervals overlap practical equivalence or a subgroup is too small, retain both. Retaining all five is allowed.

For each retained question:
- Interior minimum: bracket the lowest-NLL temperature by its tested neighbors.
- Boundary minimum: refine the adjacent interval; if the optimum remains at a supported limit, report "best within supported range." Do not exceed it.
- Multiple near-minima: retain/refine all corresponding regions.
- Flat curve: retain tested representatives, including explicit 1 and the default; do not invent a precise optimum.

Default near-tie tolerance is 0.001 NLL nats/case. Start with a 0.1 step inside selected regions, then 0.02. For intervals narrower than the proposed step, include midpoint and endpoints. Merge all questions' proposed temperatures into one next-round list and cross that list with every retained question. Preserve earlier baseline evidence; do not reuse a fresh inference under another config ID unless an explicit offline-transform record explains it.

Example only: best coarse T=1, neighbors 0.5 and 1.5 -> test 0.5–1.5 in 0.1 steps -> best T=1.1 -> test 1.0–1.2 in 0.02 steps.

Stop after three refinements, no new effective values, or improvement below tolerance at the fine resolution. Carry unresolved temperature regions forward as competing candidates. If rounding dominates tiny differences, report a plateau. If rounded zeros make NLL unusable for selection, branch to a Brier-score search on the returned probabilities, disclose the changed objective, and retain the NLL diagnostics. Never call that branch NLL-optimal temperature fitting. Its default near-tie tolerance is 0.001 in the declared multiclass Brier sum units.

### R3 — acceptance-rule sweep

Freeze question contenders. Use temperature-calibration data for fitted/minimum-NLL values and retain broad-grid/sensitivity alternatives for policy comparison; a calibration winner need not be a rejection winner.

On policy-calibration cases, compare:
- Declared unchanged R0 rule and all-accept reference.
- Maximum probability, probability gap, normalized entropy.
- Tunable confidence AND gap.
- DOCTOR concentration.
- Raw-logit margin only if available through the verified route.

Sweep distinct observed score values and all/none endpoints, preserving tied-score groups and actual comparison operators. For AND rules examine threshold pairs and report non-dominated outcomes; do not invent a scalar AURC for an arbitrary two-dimensional frontier.

Show the full attainable error/coverage frontier. Also display coverage reference levels 25%, 50%, 75%, 90%, 100% and maximum-coverage candidates with empirical error <=1%, <=2%, <=5%. These are reporting views, not deployment promises. Show actual attained coverage, denominators and uncertainty; do not interpolate a threshold through a tied group. If no point meets a requested view, report none.

Keep all empirically non-dominated candidates and practically tied alternatives. Class/tag regressions remain visible. Compare complete vectors on the same scored case IDs; report missing/failed cases separately.

### R4 — finalists and final evaluation

Freeze candidate IDs, questions, temperatures, rules and cutoffs. Evaluate only these and Q0 on the held-out role. Use the same fixed cases; the distinction is which results are now allowed into the report.

Report paired differences, class/tag breakdowns and uncertainty. A small apparent win is inconclusive when evidence is weak. Record the best tested configuration and limitations in the campaign's final decision. Creating or updating the production building block is a separate implementation, with payload/label/rule parity checks; no automatic promotion follows.

If all candidates disappoint: report the failure category and next hypothesis. Reusing held-out failures for a new design makes those cases development evidence; a later final claim needs a new campaign with fresh held-out cases.

## 5. Analysis conventions

Use source-family resampling for uncertainty, with fixed seed and 2,000 paired bootstrap samples as an engineering default. Repeated paraphrases are not independent people/requests. Exploratory multi-candidate intervals are descriptive, not simultaneous statistical guarantees.

Report all technical statuses. Preserve original returned probabilities and separately label any rounding-related normalization. Strict NLL is infinite if the expected class has exact zero probability; record rounded-zero counts and a separately named clipped diagnostic if necessary. Do not silently let a different clipping constant select the winner.

For AURC, specify tie handling and integration convention in the implementation. Retain whole tied groups; show attainable points rather than pretending exact arbitrary coverage is possible.

Annotations are for grouping and scoring only, never model inputs. Unsettled cases have no invented correct class. Report acceptance/abstention for those cases, with desired-abstention outcomes separately when explicitly annotated.

## 6. Evidence and implementation references

[S1] Chicco and Jurman (2020), majority-class pitfalls and MCC: https://link.springer.com/article/10.1186/s12864-019-6413-7
[S2] Maintainer documentation: https://scikit-learn.org/stable/modules/generated/sklearn.metrics.matthews_corrcoef.html and https://scikit-learn.org/stable/modules/generated/sklearn.metrics.balanced_accuracy_score.html
[S3] Guo et al. (ICML 2017), validation NLL fitting: https://proceedings.mlr.press/v70/guo17a.html ; author explanation: https://geoffpleiss.com/blog/nn_calibration.html
[S4] Liang, Peng and Sun (TMLR 2024), raw margins and risk/coverage evaluation: https://arxiv.org/html/2405.05160v2
[S5] Granese et al. (NeurIPS 2021), DOCTOR: https://proceedings.neurips.cc/paper_files/paper/2021/hash/2cb6b10338a7fc4117a80da24b582060-Abstract.html
[P1] RV2 implementation reviewed at commit 7a1b031191d81edc3d9ac1993a972b989e91c2e9: https://github.com/SharonLanger/laya-context-router/pull/21

Research motivates objectives and score families. Dataset sizes, round grids, tolerances, reporting reference levels and stopping budgets above are our explicit engineering decisions, not experimentally proven LAYA settings.
