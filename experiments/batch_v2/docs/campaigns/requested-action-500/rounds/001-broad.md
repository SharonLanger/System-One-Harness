# Round 001: broad screening

Status: planned, not run. Parent: current requested-action question and native default rule at source commit `f60e8b7b59ac2cc8e4ec647c39175e0292491de2`. Exact definitions: [suite.json](../../../../experiments/requested-action-500/rounds/001-broad/suite.json). Task contract: [task-definition.md](../task-definition.md).

## Fixed and changed factors

Fixed: the same 500 case strings, labels, tags, family roles, three label keys and order, model ID, English language and generic-question adapter. Rules do not modify the model request. All factors are crossed: every question/choice variant sees every rule and every temperature setting.

| ID | What changes relative to Q0 |
| --- | --- |
| q0-baseline | Exact current default question and choice descriptions |
| q1-concise | Shorter instruction |
| q2-deliverable | Ask for the requested deliverable |
| q3-direct-question | Direct question with a test-repair distinction |
| q4-imperative | Instruction to identify the requested work |
| q5-boundaries | Explicit explanation/new-tests/repair boundaries |
| q6-active-intent | Emphasize active intent, exclusions and quoted decoys |
| q7-contrast-examples | Three short contrasting examples in the instruction |
| c1-short-choices | Q0 instruction; shorter choice descriptions |
| c2-explicit-choices | Q0 instruction; more explicit choice descriptions |

Wording variants preserve the exact baseline choice descriptions. Choice variants preserve the exact baseline instruction. No label renaming, order changes or new precedence rules. Q7 tests an example-based phrasing; its examples are fixed before input review and do not come from held-out results.

| Rule | Acceptance condition, inclusive |
| --- | --- |
| r0-current | answer_confidence >= 0.50 AND gap >= 0.15 |
| r1-ungated | No acceptance gates; malformed outputs remain technical failures |
| r2-answer-060 | answer_confidence >= 0.60 |
| r3-answer-080 | answer_confidence >= 0.80 |
| r4-gap-010 | gap >= 0.10 |
| r5-gap-030 | gap >= 0.30 |
| r6-entropy-050 | normalized entropy <= 0.50 |
| r7-entropy-075 | normalized entropy <= 0.75 |
| r8-combined-loose | answer_confidence >= 0.45 AND gap >= 0.10 |
| r9-combined-strict | answer_confidence >= 0.70 AND gap >= 0.25 |

These are ten reference rules, not ten unrelated research methods. Their provisional thresholds give interpretable loose/strict comparisons. Only r0 is inherited from the current block; no paper is claimed to recommend these cutoffs. Native rules use the runtime's exact answer_confidence field and rounded derived scores. Do not silently substitute maximum class probability for answer_confidence or SDK confidence.

## Temperature rationale

Requested settings: default (null), 0.5, 1, 1.5, 2, 3, 5. Default is an unknown SDK configuration, not assumed equal to numeric 1. These are deliberately broad engineering search points on both sides of 1. They are not asserted optimal, recommended by a paper, or equivalent to generative sampling temperature.

[Guo, Pleiss et al.](https://proceedings.mlr.press/v70/guo17a.html) study fitting a scalar temperature using labeled validation data to improve confidence calibration. That motivates our separate temperature subset and NLL criterion. Applying their method to this SDK is a hypothesis: we initially compare actual returned distributions at requested settings. Offline probability rescaling needs the additional provenance/parity checks in the shared research notes.

The probe uses the pre-existing fruit input, checks all seven requests, records missing/invalid distributions, and exposes that effective settings are unknown. All seven must pass for this authored suite; otherwise write a new explicit suite rather than dropping settings without a record. Do not infer continuous support from two successful endpoints.

The protocol's `supported_range: [0.5, 5]` bounds the refinement controller's proposals; it is not evidence that every value in that interval works. Capability evidence is still pending. Every newly proposed intermediate value must pass the live probe before a subsequent run. The frozen dataset hashes remain unchanged when later rounds record new capability evidence or refinement numbers.

## Measurements and selection boundaries

- **Development (200 cases, 168 settled):** raw balanced accuracy, MCC, per-class recalls/confusion; clean/noisy/heavy and overlapping critical tags. Show the ten predeclared native rules' AC/AW/RC/RW, coverage, accepted error and correct yield. NLL/Brier here are descriptive only, not temperature-selection evidence.
- **Temperature (100 cases, 84 settled):** compare strict NLL and Brier for each retained wording independently, preserving the same support. A zero true-class probability gives infinite strict NLL, not a quietly clipped finite score.
- **Policy (100 cases, 84 settled):** select acceptance cutoffs using complete tied-score groups and risk/coverage frontiers. Compare answer confidence, maximum probability, gap, entropy, DOCTOR concentration, and confidence/gap combinations where fields are available. Existing helpers provide scalar AURC; a two-threshold frontier is not assigned a fabricated scalar AURC. No new model call is needed for another cutoff.
- **Held-out (100 cases, 84 settled):** evaluate exact frozen finalists once, including Q0. Do not inspect these predictions during earlier selection, even though the runner records them.

[Geifman and El-Yaniv](https://proceedings.neurips.cc/paper/2017/hash/4a8423d5e91fda00bb7e46540e2b0cf1-Abstract.html) motivate comparing answer coverage with error among accepted answers. We use empirical trade-offs; a threshold sweep is not their formal risk guarantee. Keep 25/50/75/90/100% coverage and <=1/2/5% observed-error views instead of forcing one deployment preference now.

[DOCTOR](https://proceedings.neurips.cc/paper_files/paper/2021/hash/2cb6b10338a7fc4117a80da24b582060-Abstract.html) supplies another way to rank likely errors from class probabilities. The implemented probability-only alpha comparator ranks by sum(p squared), accepting more concentrated distributions. It is a proposed detector, not a probability that an answer is correct. It stays in experiment analysis because the native rule schema does not have a doctor field. Optional raw-logit margin remains unavailable unless real class logits are returned; this does not block probability-based comparisons.

## Actionable next-round decisions

1. **Incomplete evidence or invalid probabilities:** retain the evidence and fix the failure before ranking. Do not select a winner from smaller accidental denominators. Resume unchanged runs or record a new attempt for changed settings.
2. **Question comparison:** always retain Q0. Keep all contenders within 0.02 of the best BA or MCC, any useful native rule trade-off, and contenders helping critical groups. Use paired source-family uncertainty before pruning; if sparse groups or intervals leave doubt, keep both. Do not force ten down to three merely for convenience.
3. **Temperature comparison:** on the temperature role only, locate each retained question's best NLL region, using Brier as a secondary check. The implemented refiner explicitly switches its objective to Brier if any tested numeric setting has infinite strict NLL; record that fallback and preserve the NLL diagnostics. If the minimum is interior, test neighboring supported values in 0.1 steps, then 0.02 steps around the remaining region. The 0.02 resolution is our local search choice, not a universal prescription. If multiple regions are within 0.001 of the active objective, retain them. Probe newly requested values before running them. A boundary optimum motivates a separately checked expansion, not an automatic extrapolation. Stop after three refinements or a flat/unresolved region and retain alternatives.
4. **Rules:** use policy data to compare and freeze native or experimental acceptance gates for surviving question/settings. Inspect per-class and noise behavior and rejection on unsettled cases. An all-reject rule has zero coverage and undefined accepted error; it cannot win by pretending to have zero error.
5. **Final check:** record selected candidates and exact definitions using the existing frozen-finalist helper before opening held-out outcomes. Report family-level uncertainty. If evidence cannot distinguish alternatives, say so; 84 settled held-out examples cannot prove a 1% error promise.

Repeatability is a separate diagnostic: a later rerun of identical settings creates a new run ID and must not be pooled as new independent cases. Do not automatically multiply the full first matrix by three. The current controller only combines its supported repeated-baseline diagnostic convention; broader repeated runs need an explicit analysis protocol.

## Execution record

Expected: 700 vectors, 500 cases, 35,000 shared model calls, 350,000 rule outcomes; setup probe adds 7 calls. The launcher has an exact inference-call cap and no wall-clock deadline. It uses existing runner replay contracts and writes every outcome to separate question/rule/configuration directories.

Record actual source commit, start/end times, probe path, run ID, status and report paths in the journal after execution. No observed score, winning temperature, elapsed time or successful live validation is asserted in this planned round.
