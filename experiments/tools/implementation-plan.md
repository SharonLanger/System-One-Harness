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

**Disk-space limitation:** this is a copy/export operation. The original V2 files
remain, so conversion initially needs additional disk space. It does not reclaim
space automatically or prevent future V2 runs from producing their current
duplicate files. Direct compact saving during future runs is a separate follow-up.

## Shared definitions, then a folder per temperature

Write a new dated folder under `experiments/exports/<campaign-id>/`, using the
existing Israel-local date/time naming convention. Never write inside the source
run folder or overwrite an existing export.

| File | What it stores |
| --- | --- |
| `definitions.json` | Run provenance and immutable definitions: inputs/annotations, questions/ordered choices, temperatures/model configs, rules and family roles, each once under its ID |
| `predictions/temperature-1.0/q7-contrast-examples.jsonl` (and other pairs) | One question at one requested temperature; one line per inference containing IDs, status, full raw response/probabilities, timing and error |
| `export.json` | Export format version, source run/revision, hashes, planned/found/success/error/missing counts and source completion status |

Use these seven temperature folders for the current grid: `temperature-sdk-default`,
`temperature-0.5`, `temperature-1.0`, `temperature-1.5`, `temperature-2.0`,
`temperature-3.0` and `temperature-5.0`. Each contains the ten question files,
named with their existing question IDs. That is 70 prediction files with 500
records each when collection is complete. An interrupted run may contain fewer
records; the manifest records planned/missing counts for each pair.

The internal config ID `t-100` means requested temperature 1.0; it is not case
100. `t-050` means 0.5. Keep these source IDs inside records and use the readable
folder names above for navigation. SDK default remains distinct from numeric
1.0 because its effective temperature is not established. Store the explicit
configuration-ID-to-folder map and each file's question/config IDs, count, byte
size and checksum in export.json; reject ambiguous folder mappings rather than
silently combining configurations.

JSONL means ordinary JSON with one record per line. Write/read one line at a
time and route it to its question/temperature file, with bounded open handles.
Do not construct a large JSON array or load all records into memory. The split
is semantic, not arbitrary 1,000-row chunks. SQLite, a new model runner, parallel
workers and new checkpoint machinery are outside this first change.

For example, a prediction line references `case-042`, `q7-contrast-examples`
and `t-100`; their complete definitions live in definitions.json. Preserve the
original inference ID. IDs are scoped to the source run/catalog, whose hash is
recorded. Never merge different questions, choice orders, temperatures, dataset
versions, fixture/live modes or repetitions just because their case IDs match.

## Prediction record contract

Use this version-1 envelope for each saved inference. The example shows a failed
call; IDs are illustrative and must be copied/resolved from the source, never
generated from this example.

```json
{"inference_id":"source-inference-id","case_id":"case-042","question_id":"q7-contrast-examples","config_id":"t-100","status":"error","raw_response":null,"error":{"message":"source error text"},"timing":{},"availability":{},"source_metadata":{}}
```

- Required fields are exactly the envelope fields shown above. Status is
  `success` or `error`, derived from source inference outcome, not rule acceptance.
  A valid `unclear` prediction is a success.
- `raw_response` contains the complete source raw response, including all original
  score/confidence channels and unknown SDK fields, without rounding or
  normalization. Preserve a returned raw response even when interpretation failed.
  Null means the source has no response; never invent a probability distribution.
- `error` is null when absent; otherwise retain the source error structure/text.
  `timing` and `availability` preserve recorded fields under their source names.
  Empty objects mean unavailable metadata, not zero duration or known availability.
- `source_metadata` retains additional inference metadata not represented above
  and not explicitly excluded below. Do not silently drop unfamiliar fields.
  Record source-to-export field mappings in the implementation documentation.
- The removal allowlist is: duplicated request/input/question/config definitions
  already verified against the shared catalog; debug-log fields outside the raw
  response; and derived baseline block/rule results reproducible by the pinned
  evaluator. Do not remove SDK raw-response fields merely because their names
  resemble logs. Unsupported or ambiguous source shapes fail validation.
- Do not add prediction records for missing calls. Preserve original inference
  identity, which also distinguishes repetitions; the catalog/run scopes all IDs.
  The raw-response value occurs only once in the envelope.

## Independent export and collection status

In `export.json`, use separate fields:
- `export_status: "complete"` means conversion and verification succeeded.
- `collection_status: "complete" | "partial"` means all planned inference
  records are present or some are missing; it does not mean all calls succeeded.
- `source_execution_status` preserves the source manifest status separately,
  including unknown/stale status. A failed report builder does not erase complete
  prediction collection.

Store `planned`, `found`, `success`, `error` and `missing` counts globally and per
partition. Require `found = success + error` and `planned = found + missing` after
unique-ID/grid validation. A successful export may therefore say:
"Export complete; collection partial; 20,000 of 35,000 records found."
Only validated published exports receive `export_status: "complete"`.

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
5. Write its response once to its temperature-folder/question-file JSONL. Preserve the entire raw response,
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

Before publication, re-read every exported line and verify it against the source
inference: identity, reconstructed request, raw-response values and precision,
errors, timing, availability and retained metadata. Verify unique IDs, partition
membership, counts and file checksums with bounded memory. Use lossless numeric
handling where needed; comparing already-rounded floating-point values is not a
precision check.

Report total source-folder bytes, source-inference bytes and final export bytes
separately, plus each partition's byte size. Five hundred records is a grouping
rule, not a file-size guarantee. The small and full-scale fixtures must exercise
long responses as well as normal responses.

The source folder remains available. Do not delete its files automatically.
Cleanup is a later explicit user decision after successful verification; the
exporter must have no automatic deletion step.
The converter makes zero model calls and imports no SDK/model loader. Export is
an offline copy, not a way to resume model inference or combine old three-choice
and new four-choice results.

## Calculate insights later

A separate offline analyzer reads definitions once and streams prediction lines
from the requested temperature/question files, using the export manifest.
Apply existing interpretation/enrichment/native rule behavior, including rounding,
to the saved responses. Reuse the existing evaluator or replay through a recorded
agent; assert that the real model loader cannot be called. Any exact legacy-rule
comparison retains the original adapter/evaluator revision as provenance.

Write summary metrics to a small summary.json and readable report. Case-level
inspection can scan the relevant question/temperature JSONL file for the chosen ID and calculate its rule
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

1. Implement the read-only exporter with shared definitions, temperature folders,
   question JSONL files and a small export manifest.
2. Test with a small synthetic V2 run: all definitions resolve, raw responses and
   precision round-trip, every record reaches its correct question/temperature file,
   valid unclear predictions and errors survive, no source byte
   changes, and no model call occurs. Reject payload/hash/ID conflicts.
3. Test interrupted input: missing records stay missing and the export reports
   partial source execution. Reject active-source use and avoid publishing a
   complete destination after converter failure or disk-full.
4. Stream a synthetic 35,000-record export to measure bytes, elapsed time and peak
   memory. Verify all 70 completed partitions have 500 records. Synthetic test outputs are temporary and are not merged into Git.
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

## Handoff to Sol

Sol implements this plan in a separate implementation PR using small testable
commits: record/catalog mapping and fixtures; streaming writer and verification;
then the PyCharm entry point and full-scale checks. This design PR authorizes no
live model run, source cleanup or changes to the running V2 experiment.
The offline analyzer follows exporter validation as described above.

If source formats, evaluator reuse or safe source-state detection cannot satisfy
this contract, stop the affected implementation and ask Astra to review the
deviation and update the plan before proceeding. Do not silently broaden scope.
Report tests, measured sizes/memory and remaining limitations when handing back
the implementation PR; do not merge it without authorization.

## Implementation refinements (2026-10-31)

V2 records no portable process PID or lock. The exporter therefore requires explicit
source_stopped=True acknowledgement; it cannot prove process liveness. It hashes
manifest, attempts/active metadata, supplied roles and the complete inference file
set/content before and after conversion and again before publication. A stale
running status is preserved, not rewritten. The caller must actually stop the run.

Initial support is generic-question replay only (choice/noul, string input).
Direct mode is rejected clearly because its inference identity includes rule ID.
The analyzer can be implemented and parity-tested on synthetic evidence now;
conversion of Sharon's actual experiment remains a later local user action.
