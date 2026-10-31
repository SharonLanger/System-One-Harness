# Runner V2 — reusable experiment matrix and reporting plan

Date: 2026-10-31  
Status: implemented with offline mechanical verification; live Mac and actual browser interaction verification remain outstanding. See [verification.md](verification.md). Original design requirements are retained below as the implementation contract.

Documentation: [Run and inspect an experiment](README.md) · [Create cases and suite files](input-authoring.md). The authoring guide provides complete matching JSON examples and an annotation workflow.

## 0. Sol implementation handoff and mandatory Astra escalation

Implementation owner: **Sol**. Sol must read this entire plan, README.md and input-authoring.md, then implement the plan on the existing PR #21 branch. This documentation update prepares that handoff; it does not start implementation. On completion, report the implementation, verification and remaining live-only checks to Sharon. Do not merge the PR without Sharon's instruction.

### Before implementation

- Inspect current main, the PR branch and applicable AGENTS.md instructions; verify the current production block/SDK interfaces and dependency availability.
- Keep implementation and task-owned verification artifacts under experiments/batch_v2/. Preserve the existing runner and production modules.
- Map the plan's requirements to concrete implementation steps and checks. Track progress and test evidence in experiments/batch_v2/verification.md.
- Build the reusable runner, the required examples, collector/reports and documentation together. Do not report completion while a planned deliverable is missing.

### When anything fails, falls short or deviates

**Sol must consult an Astra agent whenever a problem, unmet requirement, necessary plan refinement, or actual/proposed implementation deviation is discovered.** This includes unexpected test failures, incompatible interfaces, unavailable dependencies/tools, output or scoring discrepancies, missing acceptance coverage, and any need to weaken, omit or replace a planned behavior. Do not silently improvise around the plan or hide the issue by changing expected test results.

1. Pause the affected implementation step and preserve the current evidence. Independent work that cannot be invalidated by the issue may continue.
2. Spawn or resume **Astra (gpt-6-astra)** and explicitly state: "The RV2 implementation has encountered a problem or deviation from the agreed plan. Decide the recovery approach and give actionable next steps." Merely renaming a Sol agent Astra does not satisfy this requirement.
3. Give Astra the relevant plan sections, branch/commit, expected behavior, observed behavior, exact error/test output, affected files, attempted fixes, scope constraints and any proposed alternatives. Astra must inspect enough relevant code/evidence to make the decision.
4. Ask Astra to return: cause or remaining uncertainty; chosen recovery approach and rationale; ordered action items; necessary plan changes; tests/acceptance criteria proving recovery; and whether a user decision is genuinely required.
5. Record the issue and Astra's decision in verification.md. If the plan needs refinement, update the relevant sections of this document and keep README/input-authoring examples consistent. Preserve a short deviation entry describing the original requirement, why it changed and Astra's rationale rather than erasing the history.
6. Execute the agreed recovery actions and run the specified checks. Send the results back to Astra for confirmation that the issue is resolved before resuming work that depends on it. If it remains unresolved, return to Astra with the new evidence.

Astra may direct implementation-level refinements within the authorized scope. This does not authorize reversing Sharon's explicit requirements, changing production/shared code outside the stated scope, fabricating results, or merging the PR. If a recovery requires a new user decision or expanded authorization, present the concrete issue, Astra's recommendation and the required decision to Sharon. If Astra is unavailable, disclose that limitation and keep the affected work blocked; do not claim the required review happened.

Each deviation record must include: issue ID, plan section, expected versus actual behavior, evidence, Astra decision, action items, changed documents/files, verification commands/results and resolved/unresolved status.

### Completion handoff

Verify all planned deliverables and applicable checks, including the runnable fixture example and local report interaction. Summarize any deviations and Astra's resolutions. Distinguish fixture/mechanical evidence from live Mac verification and leave no unresolved issue hidden behind a completion claim. Update documentation from planned commands to verified commands only after those commands actually run successfully. Notify Sharon when PR #21 is ready for review, without merging it.

## 1. Scope and decisions

RV2 is one reusable runner for many independently defined experiments. Requested action (PR #19) and context scope (PR #20) are initial block adapters, not hard-coded runner tasks. Generic experiments define their questions, choices, cases, rules and supported configurations in JSON without new Python code.

Keep `experiments/batch/` intact. All new runner code, examples, tests, temporary files, logs and reports belong under `experiments/batch_v2/`. Import production modules read-only; do not change production code or shared dependencies. Before implementation, check current AGENTS.md, merged block interfaces and runtime contracts. The earlier PR #19 merge dependency must be checked against current main, not assumed from an old PR snapshot.

User decisions incorporated in this revision:

- An experiment studies one fixed classification task and question type. Never mix `choice` and `noul` variants in that experiment (`noul` is the SDK spelling, not JSON null).
- Variants make small changes to question wording or choice descriptions. Preserve canonical label IDs and their meanings. Wording variants preserve choices; choice-description variants preserve instructions. Record an explicit choice order and keep it fixed initially.
- Adding/removing labels, changing label meanings, or changing question type creates a separate experiment and dataset version. Such results are not ranked as comparable variants.
- No repetitions in this version: no repetition array, CLI option, folder or scheduling loop. Each case is evaluated once per selected question/configuration; rules yield their respective logical outcomes. A new launch is a new run.
- Every case has tags. Structured `noise_level` provides a mutually exclusive breakdown; tags support overlapping groups.
- All outputs from a launch share one timestamped run folder. Reports compare complete question/rule/configuration vectors and explain both model behavior and rule effects.

Real research datasets, calibrated thresholds and temperature recommendations belong to separate experiment design. Production dataset templates may remain empty. A separate, nonempty synthetic smoke example is required for learning and verification.

## 2. Authoring contract

Store each experiment under `experiments/batch_v2/experiments/<experiment-id>/` with `cases.json` and `suite.json`. IDs use lowercase letters, digits and hyphens, begin with a letter or digit, and are unique in their namespace. Reject path separators, dot segments, duplicate JSON keys, duplicate IDs, unknown schema fields and unresolved references before model loading.

### cases.json

The file contains `schema_version`, `dataset_id`, `dataset_version` and `cases`. Each case has:

- `id`: unique stable ID.
- `input`: the original string for the generic adapter, or the exact validated object required by a block adapter.
- `expected`: canonical class ID; null for cases without settled ground truth.
- `label_status`: `settled`, `taxonomy_pending`, `insufficient_context` or `out_of_scope`. Only settled, valid expected labels enter correctness metrics. Non-settled cases require expected=null in this version; put annotation rationale in optional `notes`.
- `noise_level`: `regular`, `noisy`, `heavy` or `unspecified`. Regular means no deliberate textual corruption; noisy means moderate typos/distracting text; heavy means substantial corruption or irrelevant text while the annotated meaning remains recoverable. This field measures input noise, not model success or semantic difficulty.
- `tags`: a list of unique, nonempty lowercase tag strings; an empty list is allowed. Each exact tag is one group. No substring matching or inferred tagging.
- Optional `source_family_id` linking clean and altered inputs, `split` (`development`, `calibration`, `held_out`), `desired_abstention` and `notes`. Missing family defaults to case ID; missing split is recorded as `unspecified`, never silently treated as held out.

The dataset author/reviewer sets label_status before execution; the collector uses it for scoring eligibility. Settled means an agreed expected answer, not an easy input or a guarantee that any model will answer correctly. A Claude/LAYA disagreement is a review signal, not automatic evidence of an ambiguous label. Resolve the disagreement against the task definition; retain settled if the answer is justified. Use taxonomy_pending only when class definitions or priority genuinely remain unresolved, insufficient_context for missing facts, and out_of_scope only when the task offers no valid class for that input. A defined catch-all class such as other remains an ordinary settled label. The authoring guide gives examples and explains optional review-disagreement tags. All statuses remain in operational reports; only eligible settled cases enter correctness metrics.

Suggested tags: `simple`, `misleading`, `negation`, `mixed-intent`, `missing-context`, `typos`, `irrelevant-text`. Additional language tags such as `language-en` and `language-he` can be useful. Do not require all these categories initially. Misleading text may be perfectly clean, so `misleading` remains a tag rather than a noise level. Annotation decisions are made before execution and never derived from correctness.

Only `input` reaches input preparation/the model. Expected labels, noise level, tags, split and notes never enter the model request. Random or generated input is allowed but must be materialized in cases.json before running; preserve a generation seed in notes if useful. Freeze the actual cases, not merely a recipe for regenerating them.

### suite.json

The file contains:

- `schema_version`, `experiment_id`, `dataset_id` and `dataset_version`.
- `adapter`: `generic-question`, `requested-action` or `context-scope` initially. Generic questions use an experiment-owned declaration and the shared validation/prediction/enrichment/rule interpretation pipeline. Domain-specific adapters call the real blocks and retain their input/output contracts.
- `question_type`: one supported type for the whole experiment.
- `labels`: ordered canonical IDs. Every question variant must have the same label set and order; validate through the runtime's type-specific schema. For noul, preserve the runtime's yes/no mapping instead of inventing choice criteria.
- `questions`: named complete definitions with `id`, `variant_kind` (`baseline`, `wording`, `choice-description`) and `definition`. The generic definition uses the existing question syntax (`name`, `type`, `instructions`, and type-appropriate criteria). All variants retain the same question name.
- `rules`: named entries with `id` and `definition`, using existing rule syntax and field/op/value conditions; validate compatibility with question type. Adapt names through the existing catalog without rewriting condition semantics.
- `configurations`: named entries with `id`, `model`, `temperature`, `lang`. These are the existing RunConfig settings; unknown future settings are rejected rather than silently ignored. A configuration is a complete settings object, not another independent temperature array.
- `baseline`: an object with `question_id`, `rule_id` and `config_id`, all present in their respective arrays.
- Optional `exclusions`: exact question/rule/configuration triples omitted from execution, each with a reason. Preserve excluded combinations in planning/coverage reports; do not count them as model outcomes.

Null temperature means SDK default, not zero. Freeze requested and observable effective settings separately. The current adapter omits language forwarding with null temperature, so reject null temperature with non-en language until the production adapter demonstrably supports it. No automatic model download, model fallback, unsupported-setting substitution or hidden retries.

Question type and label compatibility are mechanically validated. Whether a wording change truly preserves meaning requires the experiment author's review; syntax validation cannot guarantee that.

New arbitrary question wording/labels within a new generic experiment requires JSON edits only. A genuinely different input preparation or output contract may need another experiment-owned adapter. Adapter names are explicit; the runner does not infer a task from labels or import arbitrary code paths from JSON.

## 3. Matrix and execution

A vector is `(experiment_id, question_id, rule_id, config_id)`. Every selected vector processes the same case IDs once. Changing a question or rule creates a distinct logical batch folder; configurations live below it.

Matrix: `question variant × rule × configuration × case`.

For Q questions, R rules, C configurations and N cases, before exclusions:

- Vectors: Q × R × C.
- Logical case outcomes: Q × R × C × N.
- Inference calls with validated rule replay: Q × C × N.
- Inference calls in direct mode: Q × R × C × N.

Execution modes are independent concepts:

- `--mode live` uses the installed local SDK/model; `--mode fixture` is explicitly synthetic and never labeled live.
- `--rule-mode replay` uses validated rule replay; `--rule-mode direct` calls the underlying execution path for each rule. Default to direct until replay parity passes for the selected adapter/type.

Rules run after prediction. For replay, execute the baseline rule through the actual adapter for each question/configuration/case, capture submitted payload and raw SDK response, and retain the actual baseline BlockResult. Replay each other selected rule through existing validation, enrichment, acceptance and extraction on a fresh response copy. Reference the same inference ID in those rule results. If a baseline-rule vector is excluded, its baseline computation may still serve as an internal reference, but it must not become a scored excluded vector; disclose this in the manifest/call plan.

Parity tests must compare replay with direct execution on identical injected responses, including malformed responses, missing fields, rejection reasons and rounding. Do not reuse predictions across question or configuration IDs. Distinct configurations resolving to the same effective settings are disclosed, not silently deduplicated. Offline recollection never performs inference. Live resume can retain that same run's completed live checkpoints; it must not substitute fixture responses for unfinished calls.

Run model workers sequentially initially, reusing one loaded model for compatible settings. Use a fixed paired case order across vectors and record actual execution order. Record load/warm-up separately from prediction and rule evaluation. Warm-up calls, if any, are explicitly counted and excluded from scored cases; no hidden inference.

Print vector/case/inference counts before starting. Empty cases are valid for schema checking and dry-run planning only; do not report successful accuracy. Support maximum inference calls, elapsed-time budget and worker timeout with explicit CLI limits. Report stopped/timed-out work separately from unattempted cases. Inference-call limits include warm-up and failed attempts. Model mistakes alone do not cause a technical failure exit code; invalid config, failed writes and execution errors do.

## 4. Output layout and result extraction

Run root: `experiments/batch_v2/results/<experiment-id>/<YYYYMMDDTHHMMSSmmmZ>__<unique-id>/`.

Use UTC in the filesystem-safe timestamp, a collision-resistant suffix and exclusive directory creation. Record UTC and Asia/Jerusalem display times in metadata. Never overwrite a previous launch. All generated output is ignored by an experiment-owned .gitignore.

| Relative path | Purpose |
| --- | --- |
| `manifest.json` | Schema version, exact authored cases/suite, resolved settings, hashes, source commit/dirty status, SDK/MLX/model checkpoint versions, model-config hash, device/precision, mode, counts, start/end/status and availability notes |
| `inferences/<inference-id>.json` | Payload, raw response, enriched fields, actual baseline result, timings/errors and captured logs |
| `batches/<question-id>__<rule-id>/<config-id>/cases/<case-id>.json` | Authoritative checkpoint for one logical outcome, including inference reference |
| `batches/<question-id>__<rule-id>/<config-id>/summary.json` | Vector's overall and subgroup aggregates |
| `results.jsonl` | Combined export: one row per planned non-excluded vector/case, with explicit execution status even if no prediction exists |
| `summary.csv` | One row per vector and group, using group_type/group_value; includes overall, noise-level and exact-tag rows |
| `comparison.md` | Human-readable overall vector comparison and per-vector subgroup tables |
| `report.html` | Same data in a local standalone report with vector/group filters and narrow-screen table scrolling; no server, CDN or network required |

The structured checkpoints are authoritative; reports and exports are derived and rebuildable. They are not parsed back from console logs. Use atomic replacement for each completed inference/case checkpoint and each derived export. Resume receives the existing run path, checks frozen case/suite/adapter/source/model/runtime hashes and execution mode, rejects mismatches, and schedules only missing work. Do not append duplicate result rows on resume. Ctrl+C preserves completed work and marks outstanding work unattempted. A collector tolerates an interrupted run and reports it as partial; a failed vector is never ranked as a completed best result.

Each logical row records experiment/run/vector/case IDs, dataset version, input and expected label, label status, noise level, tags, split/family, exact question/rule/config hashes, inference ID and evaluation kind (`direct` or `rule-replay`). Preserve execution status and error separately from prediction and acceptance.

Extract final answers from structured output: requested-action uses BlockResult.data.action; context-scope uses BlockResult.data.scope; generic-question uses the existing interpreter decision answer. Preserve BlockResult.status/reason and the question decision's decided/reason fields. A rejected valid prediction is an abstention, not a technical error. A skipped block or malformed SDK response is not automatically an abstention. Valid task labels such as `other` are ordinary predictions.

Capture the raw model recommendation before rule filtering using the existing validated response/mapping logic; do not recompute it with an invented argmax/tie convention. Preserve both raw and final labels, full available probability map, answer_confidence, confidence, probability_gap, normalized_entropy and observed rule-condition values. Include action probability where available, submitted text/question/ordered label mapping, input hash, token/truncation metadata, requested/effective temperature and resolution/clamp warnings. Missing optional information is null with an availability reason; never invent tokens, logits, settings or a combined confidence score.

Record inference time, rule time and run wall time separately. Shared inference time is referenced by multiple rule rows but counted once in run totals. Vector reports may show that vector's referenced prediction latency plus its own rule latency, explicitly labeled as shared when replay is used.

## 5. Scoring: model correctness and rule effects

For every vector and every subgroup, start with matching unique case IDs. Planned subgroup size counts those cases once, regardless of how many tags each has. Show planned, attempted, valid completed, errors/timeouts, skipped, unattempted, unscored and scored counts explicitly. A scored case has settled ground truth and a valid completed prediction/decision with an interpretable raw label.

Among scored cases, use four mutually exclusive outcome cells:

| Model prediction | Rule accepts | Rule rejects |
| --- | --- | --- |
| Correct | Correct final answer (AC) | Correct answer rejected / missed opportunity (RC) |
| Wrong | Wrong final answer (AW) | Wrong answer filtered (RW) |

Therefore:

- Scored S = AC + AW + RC + RW.
- Correct final answers = AC; wrong final answers = AW.
- No final prediction / abstentions = RC + RW. RC and RW are a breakdown of abstentions, not additional cases.
- Raw model correct = AC + RC; raw model wrong = AW + RW.
- Raw accuracy = (AC + RC) / S.
- Accepted-answer accuracy = AC / (AC + AW).
- Coverage on scored cases = (AC + AW) / S.
- Correct final answers per scored input = AC / S.
- Missed-correct rate = RC / (AC + RC).
- Wrong-answer filtering rate = RW / (AW + RW).

Zero denominators display N/A, never 0% or 100%. Percentages show their denominator. For unsettled/unlabeled inputs show operational accepted/abstained counts and timings, but no correctness or false-rejection claims. If raw-label metadata is unavailable, keep the final outcome where known but mark model/rule attribution unscorable; do not silently put it in RC or RW. Report excluded/unscorable counts alongside every accuracy figure.

An RC case is evidence of a missed correct answer on this dataset, not proof that lowering a threshold is best overall. Show it beside RW and AW so users can see the tradeoff. Keep raw accuracy distinct from accepted-answer accuracy to avoid making a conservative rule look universally better just because it answers fewer cases.

## 6. Report presentation and input distribution

Default overview: one row per vector with question/rule/config IDs, planned and scored N, correct, wrong, abstained, correct-rejected, wrong-filtered, raw accuracy, accepted accuracy, coverage and prediction/rule latency. Technical statuses are visible beside the scored counts. CSV includes all columns; HTML can use expandable timing/status detail to keep the primary table readable.

Selecting one vector shows a second table with the same outcome columns and rows for:

1. All inputs.
2. Every noise level, including unspecified (a mutually exclusive partition).
3. Every observed tag, plus an explicit untagged group (overlapping membership).

Noise-level rows must sum to the overall planned count. Tag rows generally do not: an input tagged both misleading and negation appears once in each group. State this beside the table; never add overlapping tag rows into a total. Derive all filters from the same result records. Offer the same group filter across vectors for comparisons on identical case IDs. Optional combinations such as noisy AND misleading can be an explicit filter, with its exact definition/count shown; they are not required as automatic report rows.

Example of the visible count columns for one vector (illustrative arithmetic, not model evidence):

| Group | Scored | Correct | Wrong | Abstained | Correct rejected | Wrong filtered |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| All inputs | 100 | 65 | 10 | 25 | 15 | 10 |
| noise_level=noisy | 20 | 10 | 4 | 6 | 4 | 2 |
| tag=simple | 50 | 40 | 2 | 8 | 5 | 3 |

Here the model was correct on 80/100 inputs, the final answers were correct on 65/75 accepted inputs, and the rule rejected 15 correct answers while filtering 10 wrong answers. Subgroup denominators are their own scored counts, never the full dataset's 100.

Include a pre-run dataset distribution of noise levels, tags and expected labels, and per-class confusion counts among settled cases. Compare only matching dataset/split hashes and canonical labels. Different models/configurations can be intentionally compared within one experiment; their exact identities must remain visible. Cross-run merging requires explicit compatibility checks and must never silently pool different tasks, modes, label spaces or runtime versions. Show held-out groups separately from calibration/development. Do not auto-select or tune thresholds from held-out results.

## 7. Creation and usage guide

The implementation README must explain the following workflow. Commands below are the planned CLI contract, not commands available in this design-only PR.

1. Copy `examples/generic-choice/` into `experiments/<new-id>/` under batch_v2.
2. Set experiment/dataset IDs and versions; choose generic-question or a supported block adapter.
3. Write input cases, optional settled expected labels, noise levels and tags. Check labels and annotations before execution.
4. Set one question type and canonical label list. Add small wording or choice-description variants as complete definitions.
5. Add named rules and named configurations. Designate the baseline IDs. Do not add a repetitions field.
6. Validate and inspect counts, then run. A live run requires the model/SDK already installed on the Mac. Changing tasks or label meanings requires a new experiment.
7. Open the printed run-folder path and report.html or comparison.md. Filter by vector, noise or tag; inspect linked raw records when investigating a rejected correct answer.

From repository root, for an experiment named my-experiment:

```bash
python experiments/batch_v2/run.py --cases experiments/batch_v2/experiments/my-experiment/cases.json --suite experiments/batch_v2/experiments/my-experiment/suite.json --validate-only
python experiments/batch_v2/run.py --cases experiments/batch_v2/experiments/my-experiment/cases.json --suite experiments/batch_v2/experiments/my-experiment/suite.json --dry-run
python experiments/batch_v2/run.py --cases experiments/batch_v2/experiments/my-experiment/cases.json --suite experiments/batch_v2/experiments/my-experiment/suite.json --mode live --rule-mode replay
python experiments/batch_v2/run.py --resume <existing-run-folder>
python experiments/batch_v2/collect.py --run <existing-run-folder>
```

Validate-only checks schemas and contracts without writing results or loading the SDK; dry-run also prints the expanded plan/distribution without predictions. Resume uses frozen inputs in the manifest. Collector rebuilds exports/reports without the SDK. A future multi-experiment launcher can invoke this same runner per experiment; each experiment retains its own run root and metrics.

### Case example

This is a complete minimal cases.json for the generic adapter; suite.json must reference the same dataset identity and a question with fruit/other labels:

```json
{
  "schema_version": 1,
  "dataset_id": "fruit-smoke",
  "dataset_version": "1",
  "cases": [
    {"id": "case-01", "input": "I ate an apple.", "expected": "fruit", "label_status": "settled", "noise_level": "regular", "tags": ["simple"]},
    {"id": "case-02", "input": "I ate an aple.", "expected": "fruit", "label_status": "settled", "noise_level": "noisy", "tags": ["typos"]},
    {"id": "case-03", "input": "Apple released a laptop.", "expected": "other", "label_status": "settled", "noise_level": "regular", "tags": ["misleading"]}
  ]
}
```

### Required runnable example deliverable

Ship complete cases.json and suite.json in examples/generic-choice, a README and a small IDE-playable launcher that calls the same runner. The example uses the three cases above, two equivalent choice question wordings with stable fruit/other descriptions, two named rules and two supported named configurations. This is a mechanics demonstration, not a research recommendation for thresholds or temperatures. Include another type's example separately if needed; never combine choice and noul in one matrix.

The fixture example must run without MLX/model installation, exercise the real validation/enrichment/rule pipeline with explicitly injected synthetic responses, and produce 8 vectors, 24 logical outcome records and 12 fixture inference records in replay mode. Include responses demonstrating AC, AW, RC and RW across the example. Declare exact expected outcomes in a fixture manifest and assert them; never pretend fixtures measure live model accuracy. Supply a separate live command over the same case/suite files, with expected record counts but no promise about prediction correctness.

Planned fixture example command (available after implementation):

```bash
python experiments/batch_v2/run.py --cases experiments/batch_v2/examples/generic-choice/cases.json --suite experiments/batch_v2/examples/generic-choice/suite.json --mode fixture --rule-mode replay
```

The README must show both complete authored files, explain each property, give exact validated commands and tell the user which output file to open. Default IDE Play uses the clearly labeled fixture example so it works without local model setup; live is an explicit selection.

## 8. Verification and completion criteria

All new checks live below experiments/batch_v2/checks. Implement meaningful tests for:

- Generic configuration-only creation for unrelated label sets; block-adapter parity for the two initial blocks without embedding those labels in the scheduler/collector.
- Fixed type/labels/order, whole-question overrides, baseline references, incompatible rules, duplicate keys/IDs, unsafe paths, unknown config fields and rejection of repetitions. Supported noul/choice contracts are tested separately.
- Exact matrix cardinality/exclusions, once-per-case scheduling, direct vs replay counts and baseline-excluded behavior. Prediction reuse never crosses question/config IDs.
- Input/metadata separation: expected labels, tags, noise, split and notes cannot leak into submitted payloads.
- Replay parity including errors and existing rounding; no mutation of shared raw evidence.
- Four-cell arithmetic, zero denominators, mixed settled/unsettled cases, empty data, missing raw evidence, valid other labels, correct rejected predictions and wrong filtered predictions.
- Noise partitions, overlapping/duplicate tags, untagged inputs, subgroup filtering, same-case comparisons and confusion counts. Replaying another rule must not inflate subgroup case counts or shared inference time.
- Full result snapshots, safe HTML escaping of case/question text, working local report filters, and report/CSV/JSONL reconciliation with authoritative checkpoints.
- Run-folder collisions, atomic checkpoints, interrupted writes, Ctrl+C, resume hashes and no duplicates, partial collection, configuration/inference failures, hard timeout behavior and run limits.
- Required 24-row fixture example, 8 vector summaries and all expected subgroup counts. Collector rerun changes no predictions and starts no model.

Before implementation handoff, review the schema and accounting examples for internal consistency. Before implementation completion, run the fixture example, applicable tests and a browser check of the local report; report commands and outcomes honestly. Live model behavior remains an explicit Mac check. Do not claim a design review or fixture success proves live SDK compatibility or model accuracy.


## 9. Implementation deviation history

- D01: clone unavailable without credentials. Astra approved an exact-SHA connector snapshot, local verification and lease-protected Git tree/commit publication. All 76 production source files match current main by Git blob SHA.
- D02: feature branch predates merged PR #19. Astra approved integrating main into the feature branch via a two-parent commit. Production files remain identical to main; the PR changes only batch_v2.
- D03: actual browser test blocked by missing local Chromium, truncated managed browser download and cloud-browser security policy rejecting local file URLs. Browser workarounds were not attempted after that rejection. A browser check script and manual steps are supplied; browser acceptance remains explicitly open.
- D04: first focused regression command ran from the workspace rather than repo root and failed one relative-path example test. Astra was notified; rerun from repo root is the corrective action. No production change.
