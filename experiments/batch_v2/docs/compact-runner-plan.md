# Next runner: save predictions once, analyze afterward

Status: **design only; not implemented**. Prepared 2026-10-31 against main
`223b83b90c7c8f3b397c17f80f48908b579a8556` (four-choice PR #28 merged).
Owner instruction: plan the next experiment's storage and memory behavior while
preserving the current run. This document changes no executable code.

## Decision

Keep the intended grid: 500 cases × 10 questions × 7 temperature settings =
35,000 planned model calls, plus seven setup probes. The ten rules are applied
later to recorded responses, with zero additional model calls. New rules and
reports should also run entirely offline on those responses.

Save definitions once and link them with IDs. Store predictions in 70 small
SQLite files, one per question/configuration/repetition combination, with 500
case results in each for this grid. Run model workers sequentially. End all model
processes before starting analysis in a separate process. Analyze one group at a
time and produce a compact summary; retrieve individual cases on demand.

Do not change a running experiment's code, settings or files. Current results
remain useful; a later offline importer can read completed or interrupted old
runs into the new format without calling LAYA. The three-choice and four-choice
versions remain distinct datasets and cannot share prediction evidence.

## What the current implementation establishes

These are code findings, not a diagnosis of Sharon's reported memory error:

- `engine.worker` already reuses one raw inference across rules. The grid is
  35,000 model calls, not 350,000. Removing duplicate files does not reduce that
  model workload.
- Each rule checkpoint repeats the case input, annotations, derived scores and
  block result. `reporting.collect` loads all planned rows into a list, including
  placeholders for missing work. `write_reports` then builds a complete JSONL
  string and an HTML document with all case details.
- `engine.run` calls that collector in its finalization path, even after an
  interrupted/partial worker run. A stopped run can therefore encounter large
  reporting allocations before its final manifest has been saved.
- Main model execution already uses one sequential subprocess per configuration.
  Merely adding subprocesses is not a fix for the collector's memory growth.
- The separate setup probe uses one `AgentRegistry` for every requested
  temperature. Its cache key includes temperature; it can retain seven agent
  objects until the probe exits. Actual model-buffer sharing is SDK-dependent
  and has not been measured. Isolate each probe configuration as well.
- A prior synthetic sample (12 cases, all 10 question variants, 120 predictions,
  1,200 rule outcomes) projected approximately 99 MB of inference records,
  808 MB of case checkpoints and 678 MB of duplicated JSONL for the full grid.
  That is about 1.6 GB before HTML, other reports and filesystem overhead.
  These are estimates for the current format, not measurements of Sharon's run.
- The current save paths imply approximately 805,000 durable file writes before
  reports: three per prediction and two per rule outcome. File-count and write
  reduction are independent of model speed.

To identify the actual memory failure, preserve the final traceback/console
message, stage, last active task, process exit code, and current worker status.
A Python `MemoryError`, an MLX/Metal allocation failure and an OS-killed process
are different events. A missing traceback or nonzero exit alone does not prove
an out-of-memory cause. If a process is still running after a warning, check its
progress; do not infer failure from an isolated line.

## File convention and identities

Retain the existing Israel-local date/time run-folder convention and collision
suffixes. Introduce a separate compact-format version; never silently change how
an existing folder is interpreted.

| Path within a new run | Contents |
| --- | --- |
| `run.json` | Format version, run identity, inference revision, model/runtime fingerprints, requested grid, repeats and catalog hash |
| `catalog.json` | Cases and annotations, questions, ordered choices, configurations, initial rules and family roles, each stored once |
| `predictions/<config-id>/<question-id>__rep-001.sqlite` | Attempts and raw responses, linked to catalog IDs; 500 case slots in this experiment |
| `probes/<config-id>.json` | One bounded interface-probe result per requested configuration, separate from campaign cases |
| `status.json` | Small replaceable snapshot: stage, attempted/succeeded/failed/unknown counts, active IDs, timings and memory readings |
| `errors.jsonl` plus bounded backups | Errors only, referencing task/attempt IDs; same bounded policy as the current logger |
| `analysis/<analysis-id>/spec.json` | Exact rule definitions/references, analyst code version, selected role and source snapshot identity |
| `analysis/<analysis-id>/summary.json` and `START-HERE.md` | Aggregate metrics, denominators, completion status and links to selected case evidence |

Definitions appearing unchanged in an analysis spec are referenced by ID/hash;
only newly authored rules need their definitions stored there. The run catalog
is the immutable snapshot used for reproduction; it is not re-embedded per row.
The analysis identity hashes the source snapshot, analysis version, role,
settings and rules so rebuilding the same report is idempotent.

A human ID such as q0-baseline is meaningful only inside its catalog. Use an
inference task key based on case/input hash, complete question definition and
choice order, requested config/predict kwargs, model fingerprint, inference
adapter revision and repetition ID. Rule IDs are excluded from prediction
identity. Resume also checks frozen dataset/role identity. Cross-run reuse is an
explicit import with verified provenance, never an implicit global cache.

Each shard stores catalog hash plus its question/config/repetition IDs. Validate
cross-file references against the immutable catalog before opening a writer;
SQLite foreign keys cannot enforce references to a JSON file. Inside each shard,
use keys/foreign keys for attempts and selected task results.

Minimal stored record fields:

- Task: task ID, case ID, selected successful attempt ID or terminal status.
- Attempt: task ID, attempt number, started/finished time, duration, status,
  raw SDK response JSON **once**, or structured error evidence.
- Shard metadata: format/catalog hash, question/config/repetition IDs, completion
  counts, worker generation and lifecycle facts.

Preserve the full returned probability distribution and distinct SDK confidence
channels at their captured precision. Do not replace them with percentages,
rounded derived scores or only the winning label. Reconstruct the exact request
from the catalog and adapter contract; test equality with the captured SDK
payload. If an adapter transforms a prompt dynamically, store that unique
prepared text once for that task plus references, rather than assuming it can
be reconstructed. Store genuinely varying effective settings per attempt; mark
unexposed settings as unknown. Never turn requested temperature into claimed
measured temperature.

Do not persist full block results or ten enriched copies of a response. Any raw
response obtained before validation failure must remain inspectable alongside
its validation error; it is not a successful prediction. Unexpected non-JSON
values receive an explicit serialization-error record, not invented probabilities.

## Execution and recovery

Use Python's standard-library sqlite3; no database server or extra service.
Proposed new entry points live under `experiments/batch_v2/compact/` so the
existing runner and its resume behavior remain available.

1. Validate/freeze the catalog and planned task identities. Hash model assets
   once per model for this launch and reference that fingerprint across configs.
2. Run the seven setup probes sequentially, one short-lived process per config,
   using the existing non-campaign probe input. Confirm each child exits before
   loading the next. Preserve requested-versus-observed-setting limitations.
3. Start one inference worker for one configuration. It may reuse that model
   across all ten questions and write their separate shards. Reuse the current
   predictor/validators and experiment error logger; do not modify production
   loaders, gates, questions or hooks.
4. Persist a started-attempt record before invoking the model. After the call,
   atomically commit its response/error and task state. Record the raw response
   at the existing SDK boundary, then validate it. No rule evaluation, large
   reports or whole-run result list belongs in this worker.
5. On configuration completion, close every database and exit the worker. Start
   the next configuration only after process termination is confirmed.
6. Commit a final small inference status before exiting. Collection completion,
   failures and analysis completion are separate statuses. No full report is
   generated from a `finally` block.
7. Later, Run a separate `analyze_saved.py` entry point against the chosen run.
   It imports no model loader and makes no prediction calls. Reanalysis with
   new rules reads the same responses.

Initial durability policy: one completed prediction is one transaction. A
separate started-attempt transaction makes interrupted calls visible. This is
at most roughly 70,000 transactions for 35,000 calls, instead of 805,000
individual result/status writes; transaction count is not a claim about exact
filesystem sync count or elapsed time. Batch commits can be investigated later
with an explicit lost-work/retry budget, rather than silently weakening recovery.
Use journal mode DELETE and synchronous EXTRA initially; verify the actual pragma
values. Enable in-database foreign keys. Keep database caches bounded. Since
analysis follows inference, a WAL/concurrent-reader design is not required.
Temporary journal files during a transaction are normal. Share closed databases
or use SQLite's consistent backup API; never copy only a live database while
ignoring its journal.

On resume, committed successful tasks are skipped. A started attempt without a
committed result becomes interrupted/unknown; the model may have finished but
its output was not saved. Do not claim exactly-once model execution. Retries
must be explicit, counted and bounded; append a new attempt instead of replacing
evidence. Default behavior preserves failed/unknown tasks and reports the run
partial. Changing question text, choice order, model, requested temperature or
prediction adapter invalidates reuse. Analysis-only changes do not invalidate
already captured predictions. Repetition IDs intentionally prevent deduplicating
repeatability experiments.

## Bounded analysis and readable outputs

Stream raw records in small batches (initial fetch size 128) and evaluate rules
one prediction at a time. Use the existing interpretation/enrichment/native rule
functions, including their rounding semantics. Compare with the current runner
on identical captured responses before trusting the new path.

Keep aggregate confusion/counts and timing totals; do not accumulate 350,000
full result dictionaries. For ROC/risk-coverage curves and family bootstrap,
retain only scalar arrays for one permitted question/config vector, or two
vectors for a paired comparison. In this experiment that is at most 500 cases
per vector before role filtering, not all raw responses across the grid.

Filter by permitted role **before reading response payloads**. Development,
temperature, policy and sealed held-out boundaries remain enforced. Validate
hashes and all missing/error denominators. Technical failure, a predicted
unclear, and confidence-rule rejection are different outcomes.

Classification uses all four labels. Reports show accepted actionable output,
wrong actionable output, accepted unclear, and rule rejection separately.
Correctly accepted unclear counts as a correct classification and remains
non-actionable. Always-unclear/all-reject configurations cannot masquerade as
useful routers through undefined denominators.

By default, save aggregates and at most 20 example IDs per error category/group.
A case-detail command reconstructs one case's input, prediction and rule result
from IDs. A bounded export can materialize an explicitly selected subset when
needed. No default whole-run JSONL duplication and no HTML containing every
case. Native per-case decisions are reproducible from pinned rule/evaluator
versions; if an audit export is requested, it contains compact IDs/outcomes,
not copied prompts and raw responses.

## Memory limits, processes and progress

Default model concurrency is **one**. Multiple model processes may hold multiple
sets of weights and caches; process isolation does not provide extra physical
memory. MLX uses shared CPU/GPU memory. Parallel model execution is a later
measured optimization, not the proposed response to a memory error.

Measure parent RSS and worker RSS separately. Where installed MLX supports it,
record active/cache/peak device-memory counters too; Python-only allocation
tracking is insufficient. Do not add RSS and MLX counters into one purported
physical-memory total because they can overlap. Record availability/version.
Sample on a time interval and persist bounded summaries, not one verbose record
per prediction.

The small supervisor receives IDs/counters only, with bounded IPC. It does not
retain model results. The worker drops references to each response after its
transaction and releases temporary objects. If measured memory grows with task
count, checkpoint and recycle the child between committed groups within the
same configuration. Make the recycling interval configurable after the pilot;
reloading for every case would be unnecessarily expensive. Freeze and record
that policy. Never auto-repeat a persistent allocation failure indefinitely.
A soft budget can stop scheduling and preserve state, but cannot guarantee that
a single allocation will not fail before the next sample.

Console progress should distinguish:

- `loading` / `probing` / `predicting` / `saving` / `analyzing` / `complete` / `partial`;
- current question/config and repetition;
- calls attempted versus responses durably saved, failed and unknown;
- overall planned calls, per-configuration progress, elapsed time and phase ETA;
- sampled memory and last completed task time.

Update an in-place terminal line or an occasional PyCharm console line (initially
10 seconds), and replace status.json at the same interval. Count model tasks,
not case IDs or ten-times-larger rule outcomes. Display ETA as an estimate based
on measured throughput after warm-up; loading and analysis have separate timing.
The model worker's exit alone does not mean analysis completed.

## Existing-run import and rollout

An offline importer reads the old manifest and streams only `inferences/*.json`.
It does not invoke the old collector or open all 350,000 rule files. Verify case,
question, config, request payload, raw response, run mode, hashes and adapter
provenance. Store original inference ID/source run/revision and response checksum.
Mark data captured by the legacy adapter as such; reject conflicts or duplicated
IDs with different responses. Legacy raw errors remain errors. Missing inference
files stay missing. Do not trust a stale running/completed manifest over records.
Old inferences may contain embedded debug traces; exclude those from compact
storage because raw outputs and request evidence are preserved, while keeping
the original folder available. Never delete or rewrite the source automatically.

Imported evidence can be analyzed without LAYA. Resuming it for more inference
requires verified request parity with the new adapter, including configuration
and runtime/model fingerprints. If that equivalence is not established, preserve
it for separate analysis and start a fresh collection; do not silently mix paths.

Rollout order:

1. Implement normalized catalog/shard storage and safe recovery under the
   experiment directory. Tests use synthetic responses only.
2. Add the isolated inference-only launcher and sequential probes; prove payload
   parity and absence of rule/report work in the worker.
3. Add streaming offline analysis and bounded reporting; prove parity with the
   current native-rule outputs and metrics, including unclear behavior.
4. Add progress, memory telemetry, phase statuses and the read-only legacy
   importer. Keep new entry points opt-in until validation is complete.
5. Run a synthetic full-size 35,000-response / 350,000-rule benchmark to measure
   file count, bytes, elapsed collection/analysis time and peak RSS. No model calls
   are needed for this scale test, and generated outputs stay out of Git.
6. On the Mac, begin with the same 500 inputs, one question and one temperature.
   Measure loading/prediction/write times and process/device memory. This pilot
   is for runtime and storage verification; use only permitted roles for scientific
   selection. It must not silently remove other planned question/temperature pairs.
7. If memory is stable and integrity checks pass, schedule the remaining grid in
   resumable groups. Reuse a pilot only when all inference identities match and
   it is explicitly part of the same run; otherwise keep it as a separate pilot.

A 35,000-call run is still permitted. Stage boundaries make it observable and
resumable; they are not an automatic scientific pruning policy.

## Acceptance checks before replacing the current default

- Round-trip every captured raw field and its numeric precision; reconstruct
  request payload exactly. No annotations appear in the model prompt.
- Exactly 35,000 unique task slots for this grid, plus separate probe counts;
  no rule/analysis-only change adds model calls. Retries have explicit counts.
- About 70 prediction databases plus a small number of catalogs/reports, not
  385,000 checkpoint files. Temporary journals and bounded diagnostic files are
  counted separately. Compare actual bytes with the same synthetic legacy data;
  target at least 80% reduction, not a promised live-run size.
- Kill a worker before call, during call, before/after result commit, and at shard
  boundaries. Reopening yields valid committed rows and explicit unknown attempts.
  Disk-full, read-only output and corrupt/mismatched input fail clearly without
  a false completed status. Restart does not duplicate committed responses.
- The parent and analyzer have bounded memory as row count increases from 1,000
  to 35,000. Initial non-model RSS budget target: 256 MiB per process, to be verified
  on the actual runtime; record measurements rather than declaring an unmeasured
  guarantee. Dataset catalogs and per-vector scalar arrays have explicit limits.
- No second model worker overlaps the first, including probes/recycling. Force
  MLX allocation failure in a fake loader and verify bounded diagnostics/partial
  status. Unit tests never load a real model or tokenizer.
- Analysis runs with the model loader patched to fail on any call and still
  reproduces all supported native gate decisions, confusion/NLL/Brier metrics,
  missing denominators and unclear-versus-rejected distinctions.
- Held-out payloads are never opened during earlier analysis roles. Rebuild and
  importer are idempotent. Old/new format dispatch is explicit and old artifacts
  remain readable through their supported reader.
- Store no raw test outputs or machine-specific evidence in merged source. Put
  validation summaries in the PR and keep reusable test code and documentation.

## Sources and engineering choices

- Repository inspection: engine.py worker/run/finalization, reporting.py
  collect/write_reports, research/probe.py run_probe, and
  src/laya_context_router/laya/registry.py at the source revision above.
- [SQLite atomic commit](https://www.sqlite.org/atomiccommit.html) describes
  transaction recovery and filesystem assumptions. It motivates transactional
  checkpoints; it does not promise immunity to broken storage.
- [SQLite synchronous settings](https://www.sqlite.org/pragma.html#pragma_synchronous)
  distinguish durability modes. The initial DELETE/EXTRA choice preserves strong
  sync behavior while removing duplicated writes.
- [MLX unified memory](https://ml-explore.github.io/mlx/build/html/usage/unified_memory.html)
  explains shared CPU/GPU memory. Sequential model processes are our engineering
  choice to bound concurrent model allocations, not a measured speed claim.
- [MLX memory APIs](https://ml-explore.github.io/mlx/build/html/python/memory_management.html)
  expose device memory accounting; use only capabilities present in the installed
  version. Do not import MLX in offline analysis just to obtain telemetry.

Remaining empirical questions: the actual traceback/stage of the reported memory
error; steady/peak memory on Sharon's Mac; real response sizes; and measured
throughput after duplicate storage/report construction are removed. None prevents
implementing and testing the isolated storage/analysis design.
