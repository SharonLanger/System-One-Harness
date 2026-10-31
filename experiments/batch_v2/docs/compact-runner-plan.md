# Simple offline export of V2 results

Status: **design only; not implemented**. Revised at Sharon's request on
2026-10-31. This supersedes the earlier SQLite/new-runner proposal in this PR.

## Scope

Let the current experiment finish using its current code. Build a small,
standalone tool afterward that reads its saved results and produces a compact
copy in a different folder. Keep V2's launchers, storage, workers, rules and
reports unchanged. Do not update code used by a running experiment.

The experiment still has 500 inputs × 10 questions × 7 temperature settings =
35,000 planned model responses, plus separate setup probes. Each distinct
question/temperature/input needs its own response. All ten rules can use that
same response later. This export reduces duplication and makes sharing and
analysis easier; it does not accelerate the already running model or stop V2
from writing its current files.

## Just two data files and a small status file

Write a new dated folder under `experiments/exports/<campaign-id>/`, using the
existing Israel-local date/time naming convention. Never write inside the source
run folder or overwrite an existing export.

| File | What it stores |
| --- | --- |
| `definitions.json` | Run provenance and immutable definitions: inputs/annotations, questions/ordered choices, temperatures/model configs, rules and family roles, each once under its ID |
| `predictions.jsonl` | One line per saved model inference: inference ID, case ID, question ID, configuration ID, status, full raw response/probabilities, timing and error |
| `export.json` | Export format version, source run/revision, hashes, planned/found/success/error/missing counts and source completion status |

JSONL means ordinary JSON with one record per line. A file containing 35,000
records is reasonable when written and read line by line. Do not construct one
large JSON array or load all records into memory. SQLite, a new model runner,
parallel workers and new checkpoint machinery are outside this first change.

For example, a prediction line references `case-042`, `q7-contrast-examples`
and `t-100`; their complete definitions live in definitions.json. Preserve the
original inference ID. IDs are scoped to the source run/catalog, whose hash is
recorded. Never merge different questions, choice orders, temperatures, dataset
versions, fixture/live modes or repetitions just because their case IDs match.

## Standalone flow

Proposed entry point: `experiments/tools/export_v2_results.py`, with ordinary
Python standard-library code and an importable export function. It receives a
source run folder and a separate destination parent. Expose a small settings
section for PyCharm Run; no editing V2 is required. Implement it in a separate
PR from this design.

1. Wait until the source process has stopped. It can be a completed or interrupted
   run; both are exportable, with the difference recorded explicitly.
2. Read the manifest and any available campaign/role metadata. Store frozen
   definitions once, preserving original version and provenance. Validate their
   hashes. If roles are not available, ordinary export can proceed, but
   role-dependent analysis must refuse until a matching role map is supplied.
3. Walk only `inferences/*.json`, opening one file at a time. Do not call the V2
   collector and do not read the 350,000 rule-result files. Resolve IDs using the
   original definitions and inference-identity convention; fail on conflicting
   IDs or an inference that cannot be mapped reliably.
4. Verify each saved request payload against the reconstructed request from its
   case/question/config definitions. The first implementation supports the
   generic-question/string-input format used by requested-action-500. Unsupported
   adapters or mismatches must fail clearly rather than silently discard unique
   request information. Do not guess requested versus effective settings.
5. Write its response once to predictions.jsonl. Preserve the entire raw response,
   numeric precision, distinct confidence channels, timing, availability fields
   and errors. Drop duplicate prompt/question copies, embedded debug logs and
   full baseline block results; the raw response plus pinned evaluator is the
   evidence used to calculate rules later. Keep malformed-response errors visible.
6. Derive missing-counts from the planned grid, not the source manifest's status
   alone. Preserve the source attempt count where available; do not claim it can
   be reconstructed from successful response files. Unknown/interrupted attempts
   remain unknown. Missing responses do not become successful predictions.
7. Write files in a temporary destination, then publish the finished export only
   after all validation and hashes pass. On failure, leave the source untouched
   and no apparently complete export. Rerunning the converter may start fresh;
   a converter-resume system is unnecessary for this first version.

The source folder remains available. Do not delete its files automatically.
The converter makes zero model calls and imports no SDK/model loader. Export is
an offline copy, not a way to resume model inference or combine old three-choice
and new four-choice results.

## Calculate insights later

A separate offline analyzer reads definitions once and streams prediction lines.
Apply existing interpretation/enrichment/native rule behavior, including rounding,
to the saved responses. Reuse the existing evaluator or replay through a recorded
agent; assert that the real model loader cannot be called. Any exact legacy-rule
comparison retains the original adapter/evaluator revision as provenance.

Write summary metrics to a small summary.json and readable report. Case-level
inspection can scan the JSONL file for the chosen ID and calculate its rule
results on demand. Do not save the prompt and raw response again for each rule.
For a requested per-case rule export, save only IDs and compact decisions.

Preserve the development/temperature/policy/held-out analysis boundaries. Before
using a response in metrics, resolve its case role and authorize access. The full
prediction export contains held-out evidence and must be treated as sealed raw
data; share the development-only report first for tuning. Correctly predicted
unclear is a scored non-actionable answer, separate from confidence-rule rejection
and technical failure. Missing work keeps the report partial, with honest
metric denominators.

Aggregate confusion/count metrics incrementally. For a risk-coverage curve or
paired comparison, retain only the required scalar scores for the permitted
vector(s), not all raw dictionaries. This avoids the current reporter's
whole-run list and HTML allocations. It does not diagnose the memory error
reported during the existing run; that still needs the traceback and stage.

## Small implementation and validation sequence

1. Implement the read-only exporter and its two-file-plus-status format.
2. Test with a small synthetic V2 run: all definitions resolve, raw responses and
   precision round-trip, accepted unclear and errors survive, no source byte
   changes, and no model call occurs. Reject payload/hash/ID conflicts.
3. Test interrupted input: missing records stay missing and the export reports
   partial source execution. Reject active-source use and avoid publishing a
   complete destination after converter failure or disk-full.
4. Stream a synthetic 35,000-record export to measure bytes, elapsed time and peak
   memory. Synthetic test outputs are temporary and are not merged into Git.
5. Use the converter on this experiment after it stops, then add the small offline
   analyzer and verify metric/native-rule parity on the synthetic reference.

Do not promise a storage ratio before measuring actual responses. A later
inference-only writer could emit this same simple format directly, avoiding V2's
intermediate copies on future experiments. That is a separate decision after
this exporter and analysis path work; it is not part of this first implementation.

## Current-run guidance

Preserve the running experiment and let it progress. No installation, code update
or storage conversion is needed while it runs. If prediction collection finishes
but the old report builder fails, the saved inference files may still be usable
by this offline exporter. Preserve the traceback and source folder; report
failure must not be confused with loss of every saved model response.
