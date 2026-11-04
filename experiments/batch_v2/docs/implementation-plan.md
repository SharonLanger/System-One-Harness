# Implementation plan before the first real campaign

Status: Track A tooling implemented for review; live Mac and browser acceptance remain pending. See [implementation evidence](track-a-verification.md) and [research interfaces](../research/README.md).
Scope: experiments/batch_v2/ only.

Read [README](README.md), [workflow](workflow.md), [scoring](scoring.md) and [records and handoffs](records-and-handoffs.md) before implementing.

## Track A — prepare, verify and merge the experiment tooling

Complete A1–A7 in a separate implementation PR before authoring and running the first full research campaign. The documentation and synthetic fixture checks can be completed without choosing the first real classification question.

Runner V2 already exists on main: PR #21 merged at 83211fd88d10e4c0854797dec47df33ce8d04ea5. It supplies matrix execution, raw response capture, replay, checkpoints, collection and noise/tag/split reports. Its fixture/regression results are recorded in verification.md (historical material; see docs/cleanup-local-files.md); they are not new results produced by this handbook.

Recheck the current code before implementation. At the reviewed version:
- Generic-question takes a nonblank string; existing block adapters take objects.
- Canonical labels and order stay fixed within an experiment; wording and choice-description variants are separate.
- split is development/calibration/held_out.
- Existing choice-rule fields include confidence, answer_confidence, action.act_probability, probability_gap and normalized_entropy.
- DOCTOR and raw-logit margin are not recognized rule fields.
- Effective temperature is not exposed at the captured SDK boundary.
- No built-in repetitions dimension exists.

Import production modules read-only. Pure score functions must have no runner, file or model dependency. Add new analysis via an experiment-owned reader/replay layer; do not put unsupported fields in current suite JSON. Do not copy experimental code into production during this work.

A1 includes a small Mac capability check. It is an assigned verification task, not missing knowledge that Sharon must invent. Probability-only live sweeps remain the sufficient fallback.

### A1 — implement a response reader and capability probe

Proposed location: research/records.py and research/probe.py.

Read the frozen manifest, inference records and cases; resolve label order and source inference IDs. Extract all available class probabilities and raw labels, not only the winner's confidence. Missing fields have explicit reasons.

On the Mac, make a small, counted probe with already-installed assets. Determine supported temperature settings, observable effective settings, output precision, probability normalization and whether logits are available. This is an interface check, not a test of whether the model's percentages are "genuine."

Choose one temperature route: captured logits; verified full-precision probability transformation with known T0; or live temperature matrix. The live route is sufficient and must work without the optional routes. Never install or upgrade SDK/model packages automatically.

Done when a capabilities report selects the route and parity compares offline transforms with real returned probabilities at selected temperatures within a documented precision tolerance.

### A2 — implement pure scores and metrics

Proposed files: research/scores.py and research/metrics.py. Use existing repository language/runtime conventions; do not add a production dependency merely to obtain a formula.

Scores:
- Maximum probability, gap, normalized entropy and DOCTOR G=sum(p²).
- Raw-score margin if supplied real logits.
- Separate answer_confidence from max probability when binning differs.

Metrics:
- Confusion counts, per-class support/recall, accuracy, balanced accuracy, macro F1 and multiclass MCC.
- NLL and multiclass Brier sum convention (no undocumented scaling).
- AC/AW/RC/RW, coverage, accepted error and correct-accepted yield.
- Gate MCC as a secondary diagnostic, with degenerate cases flagged.
- Scalar risk/coverage curves and explicitly named grouped-step AURC.

Define MCC as (c*s - sum(p_k*t_k)) / sqrt((s²-sum(p_k²))*(s²-sum(t_k²))), with c=trace, s=total, p=predicted totals and t=true totals. Return zero plus a degeneracy flag for a zero denominator, matching the declared compatibility convention; empty input is unavailable. For a subgroup lacking classes, surface its support and comparability limitations.

AURC convention: sort scores toward acceptance; add complete tied-score groups; after group j, use observed risk r_j and coverage increment delta_c_j. Report sum(delta_c_j*r_j) as grouped-step AURC. Do not silently compare it with another tie/integration convention. AND-rule threshold pairs yield a frontier, not a fabricated scalar ordering.

Preserve original probabilities; validate finite values and labels. Small normalization corrections must be explicit. Record exact/rounded zeros and keep strict NLL separate from any clipped diagnostic.

Done when golden examples distinguish good classification, majority prediction, confidently wrong probabilities and useful versus harmful rejection.

### A3 — implement frozen analysis roles and held-out protection

Proposed file: research/protocol.py.

Load source-family roles from a sidecar, without adding unsupported fields to cases.json. Every calibration family belongs to exactly one of temperature or policy calibration. No family crosses roles.

Filter IDs before loading prediction evidence into selection routines. Default tuning report includes only development and the permitted calibration role. Do not derive selection metrics from RV2's all-input summary, which includes held-out cases. The final-report path requires a frozen-finalists artifact.

Done when a test with tempting held-out results cannot change question, temperature or threshold selection. All full-case launches still use identical frozen input bytes.

### A4 — implement temperature refinement

Proposed file: research/temperature.py.

Implement the blueprint's explicit initial grid, adjacent bracketing, 0.1 and 0.02 refinement, multi-region ties, boundary handling, 0.001 NLL tolerance and three-refinement cap. Parameterize and record these choices before the campaign starts. Combine per-question candidate temperatures into one shared next-round list.

Optional automatic fitting can use the verified offline route. Keep fitting objective NLL distinct from policy selection. If rounded zeros make NLL unusable, implement the explicitly labeled Brier-search branch with its own recorded tolerance; retain strict NLL diagnostics. Do not treat default/null temperature as a numeric point without knowing its effective value. Preserve requested/effective setting provenance and rounding.

Done when synthetic convex, flat, tied and boundary-minimum curves produce the specified next candidates and terminate; no unsupported setting is silently substituted.

### A5 — implement threshold sweeps and paired reports

Proposed files: research/policies.py and research/analyze.py.

Evaluate existing conditions through verified replay where possible. Experimental scores use isolated pure evaluators and separate result records. No production schema changes.

Sweep distinct score thresholds with ties intact, and threshold pairs for AND. Build empirical error/coverage frontiers, per-class/group reports and the blueprint's reference views. Missing risk targets return no candidate; all-abstain never reports perfect accepted accuracy.

Keep inference counts separate from logical rule outcomes. Add immutable round IDs and campaign IDs through the research sidecar, without inserting unknown fields into RV2 suite JSON. Separate experimental policy results from runner-native results. Validate model/question/data hashes before combining rounds.

Done when shared evidence, direct/replay parity and all denominators reconcile. Add a narrow-screen HTML view or use the current report facilities without changing their established columns/meaning.

### A6 — implement next-round decisions and final freeze

Proposed file: research/next_round.py.

Input: campaign protocol, allowed-role results and decision history.
Output: the completed next-run section in the numbered round record plus a proposed runner-compatible suite JSON; no automatic model invocation by default. Create/update the campaign journal using the shared templates, preserving prior entries.

Implement keep-both behavior for unresolved comparisons, protected Q0 baseline, critical-group retention, temperature stopping and complete provenance. The generated JSON must pass the actual RV2 validator. Persist a finalists artifact before unlocking held-out analysis.

Done when replaying the same evidence produces the same next-round decisions, with no private inference, case mutation or held-out-dependent selection.

### A7 — evidence export, verification and handoff

Implement the compact evidence export and durable handoff described in [records-and-handoffs.md](records-and-handoffs.md), including archive manifests and hashes. A local ignored results directory alone is not a complete shared handoff. Preserve full raw logs; publish exact records needed to reproduce metrics and decisions.

All tests remain in experiments/batch_v2/checks/ or an experiment-owned subdirectory.

Required examples:
- 90 no/10 yes with constant-no predictions: accuracy 0.9, balanced accuracy 0.5, MCC 0 with degeneracy noted.
- Perfect and deliberately inverted binary predictions; multiclass confusion example.
- All-accept, all-reject, correct-only acceptance and wrong-only acceptance.
- Tied scores, absent subgroup classes, empty data, missing probabilities and zeros.
- DOCTOR [0.7,0.2,0.1] -> 0.54; uniform K-class -> 1/K.
- Temperature preserves argmax except declared ties/numerics; live parity for supported offline routes.
- No leakage of tags/labels into model requests or held-out evidence into selection.
- Same source-family splits and case hashes across rounds; interrupted/incomplete runs cannot become winners.

Run relevant existing RV2 checks after integration. Report fixture/mechanical evidence separately from live Mac evidence. Verify the change scope is restricted to experiments/batch_v2/. Document commands only after they exist and are exercised.


## Track A completion checklist

- [x] Pure metrics and DOCTOR pass golden checks.
- [x] Reader captures labels/probabilities with honest availability metadata.
- [x] Tuning paths cannot consume held-out evidence.
- [x] Broad/refined temperature proposals and threshold sweeps terminate and preserve provenance.
- [x] Generated suites validate with the actual runner.
- [x] Reports distinguish supported metrics, unavailable values and technical failures.
- [x] Campaign/round records and evidence exports let a different agent reproduce decisions.
- [x] Applicable RV2 regression checks pass; changed files remain under experiments/batch_v2/.
- [ ] Local HTML report behavior is checked, including the outstanding browser acceptance from PR #21.
- [ ] Capability probe selects a verified Mac route before the first full live campaign; pending live work is explicitly recorded.
- [ ] Implementation PR is reviewed and merged under Sharon's instruction.

A code change may be ready for review while the Mac probe remains pending, but it is not yet a ready-to-run live campaign. Do not claim fixture tests establish model accuracy.

## Track B — define the first real use case after tooling preparation

This is the next design discussion, not part of the generic implementation PR.

1. Complete [task-definition.md](templates/task-definition.md): desired behavior, exact input text/context, class meanings, boundaries, acceptable uncertainty and fixed choice order.
2. Choose generic-question. Define Q0 as the initial authored reference, then equivalent wording and description alternatives. An existing block is background evidence, not a required execution path.
3. Define R0 and initial configurations, engineering budgets/tolerances and critical subgroups.
4. Give the completed contract and [input-authoring.md](input-authoring.md) to the input agent. Generate, independently review and freeze cases/roles. No case list exists yet.
5. Copy the [campaign README](templates/campaign-readme.md), [journal](templates/run-journal.md) and [run record](templates/run-record.md). Populate only known facts; use not-run for future rounds.
6. Validate/dry-run exact files, complete the Mac probe and run the broad/refined campaign following the workflow.
7. Freeze finalists, inspect held-out results and write the [final decision](templates/final-decision.md).
8. Use the chosen question/choices/rule/configuration to design a separate production building block. Preserve exact payload behavior or rerun parity evaluation.

Deliverables are a generic classifier experiment and evidence-backed configuration. Integration into a production block is subsequent work with its own tests.

## Deferred optional extensions

Raw logits and offline temperature fitting are useful optimizations, not prerequisites for the main probability-based route. Conformal sets, choice-order permutation campaigns, built-in repetitions and automatic deployment remain outside the first implementation.

## Implementation evidence

Review current source and repository instructions before editing:
- [schema.py](../schema.py)
- [engine.py](../engine.py)
- [reporting.py](../reporting.py)
- [Runner usage](../README.md)

Proposed research filenames are planned additions. Only the commands in the current runner README are existing interfaces. New commands must be documented after they are implemented and exercised.
