# Runner V2 — batch matrix execution plan

Date: 2026-10-31  
Status: plan only; this PR adds this Markdown file and does not implement the runner.

## Scope

This standalone document contains only the Runner V2 section extracted from the LAYA batch experiment blueprint. It plans the runner for [requested action (PR #19)](https://github.com/SharonLanger/laya-context-router/pull/19) and [context scope (PR #20)](https://github.com/SharonLanger/laya-context-router/pull/20).

Keep the existing `experiments/batch/` runner and its examples intact. Future implementation, its checks, inputs, logs and reports belong under `experiments/batch_v2/`. Existing production modules may be imported read-only; no production or shared-dependency changes are included.

Question wording, choice descriptions, candidate rules, temperature sweep values and research recommendations belong to the separate experiment-design discussion. This plan defines how the runner consumes those values, not which experiments to select. Another agent owns case generation; initial case arrays remain empty.

Publishing this plan does not implement or run it. Before later implementation, recheck applicable AGENTS.md and current block interfaces. Use the existing block overrides and preserve their question type and stable label sets.

### A1. Two authored files

**File 1: cases.json**

Contains task-specific datasets. Each dataset has an ID, version and a cases array, left empty in the initial template. The two tasks may use overlapping prompts, but their expected labels remain separate.

Each future case provides:

- Stable case ID and original input object.
- Expected canonical label when the taxonomy is settled.
- Label status: settled, taxonomy_pending, insufficient_context or out_of_scope.
- Tags, such as language, typo level, noise, decoys, negation and mixed intent.
- Source-family ID linking a clean prompt to its paraphrases/noisy versions.
- Fixed split assignment: development, calibration or held_out.
- Optional desired-abstention annotation, separate from a class label.

Only the input object reaches the block. Expected labels, tags, split names and generation notes never enter the model request.

**File 2: suite.json**

Contains two task definitions. Each names its dataset and lists:

- Complete question/choice variants, including explicit ordered criteria.
- Named rule variants with existing condition syntax.
- Temperature values.
- Fixed model identity and language configuration.
- Repetition count, execution mode and optional run limits.
- Stable IDs, a baseline designation and any explicit exclusions.

One command loads these two files, runs either task or both, and collects results. The proposed command is illustrative, not available yet:

`python experiments/batch_v2/run.py --cases cases.json --suite suite.json`

The question array is the user's first vector: each entry is one complete question with its choices. A wording-only variant keeps criteria unchanged; a choice-only variant keeps instructions unchanged. This makes those changes independently attributable.

### A2. Cross every selected factor

This is a **Cartesian product**, also called a [full factorial design](https://www.itl.nist.gov/div898/handbook/pri/section3/pri333.htm):

`question/choice variant × rule × temperature × repetition × case`

Every selected question variant is evaluated with every selected rule and every selected temperature, using identical case inputs. Repetition reruns identical model inputs; changing wording creates a new variant.

A logical batch is a specific question/choice variant plus a specific rule. Each gets its own folder:

`results/<run-id>/<task>/batches/<question-variant>__<rule>/`

Below that batch, retain separate temperature and repetition results. Thus changing a question, choice presentation or rule produces a distinct batch folder, while one launch manages the whole matrix.

The top-level collector compares the folders. Compare configurations within each task; do not pool their different label spaces into one accuracy score.

### A3. Evaluate all rules without unnecessary inference

The current rules run after prediction. They are not instructions sent to LAYA.

Recommended mode:

1. Invoke the real block once for each case, question variant, temperature and repetition, using its baseline rule.
2. Capture the submitted payload and original SDK response through existing logging or an experiment-owned wrapper around the existing loader boundary.
3. Retain the actual baseline BlockResult.
4. Replay each alternative rule through the existing validation, enrichment, acceptance and extraction functions on a fresh copy of that same response.
5. Store every rule result in its own batch folder, with a reference to the shared inference record.

All logical combinations still exist. Rule-only differences use identical model evidence. Explicitly mark alternative results as **rule replay**, rather than claiming each was a new block invocation.

Before enabling this optimization, mechanical tests must prove replay matches direct block execution on the same injected SDK response, including rejection reasons, invalid responses and rounding. If parity cannot be established, use direct block execution for every matrix cell until resolved.

Do not reuse predictions across question variants, temperatures or repetitions. Those are genuine model evaluations. Do not inject recorded responses into runs labeled live.

### A4. Scheduling and completion

- Load a locally available model once per compatible temperature/language worker and reuse it. Run workers sequentially initially to bound model memory.
- Rotate or randomize worker order between repetitions with a recorded scheduling seed. Pair case order across compared variants. The scheduling seed is not a model sampling temperature.
- Use one common runner and adapters to the two existing block entry points; do not fork a different runner for each question.
- Begin with separate block calls. An SDK call containing many questions is an optional later throughput comparison requiring output-parity checks.
- Record model load/warm-up time separately from measured prediction and rule time.
- Checkpoint every completed inference and rule evaluation. Ctrl+C preserves completed work and marks outstanding work unattempted.
- Provide resume keyed by frozen input/configuration/model hashes; reject mismatched resumes.
- Print the expanded run count before starting. Empty cases permit schema validation/dry-run only and produce zero predictions, not a successful accuracy report.
- Support optional maximum calls, elapsed-time budget and per-worker timeout. Report a timed-out attempt separately from untouched cases.
- No automatic model download, model fallback or hidden retries. Configuration failures are distinct from inference errors and abstentions.

Let Q be the number of question/choice variants, R the rules, T the temperature settings, P the repetitions and N the cases for one task:

- Logical decisions: `Q × R × T × P × N`.
- Model calls in validated rule-replay mode: `Q × T × P × N`.

Read these counts from the suite; do not hard-code a specific experiment matrix. Counts are before skips or effective-setting duplicates. Measure a short pilot to estimate duration; do not promise a half-hour completion time.

### A5. Records and collector

The run manifest freezes exact case and suite contents, hashes, source revision, SDK/MLX versions, checkpoint revision, model-config hash, device, precision, timezone and execution mode. Record UTC times plus Asia/Jerusalem display times.

Each inference record preserves:

- Task, case, source-family, split, variant, temperature and repetition IDs.
- Exact submitted text and question, ordered label mapping and input hash.
- Requested temperature, effective temperature, resolution source and any clamp warning.
- Raw SDK response; full probability map; selected label; answer_confidence; confidence; action probability when available.
- Existing enriched probability_gap and normalized_entropy.
- Actual baseline BlockResult, SDK errors and captured logs.
- Available token/truncation metadata and timing.

Each rule record preserves rule definition/hash, source inference ID, observed condition fields, pass/fail reason and final label or abstention.

Optional fields are null with an availability explanation when absent. Do not invent logits, token counts, effective settings or a combined confidence score.

Output includes a machine-readable manifest, raw records, per-batch summaries, a merged row-level export, and a human-readable comparison. Collector comparisons require matching dataset/split hashes, canonical labels and compatible model/runtime identities.
