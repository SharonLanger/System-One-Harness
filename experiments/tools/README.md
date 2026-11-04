# Compact V2 results

Open `export_v2_results.py` in PyCharm. Set SOURCE_RUN to the stopped experiment's
result folder, DESTINATION_PARENT to `experiments/exports/requested-action-500-v2`
(or another separate folder), and optionally ROLES_FILE to the matching frozen
`calibration_roles.json`. Confirm the model process has stopped, then set
SOURCE_STOPPED=True and click Run. No command-line arguments are needed.

The original run stays in place. Exporting needs additional disk space. This tool
never deletes originals, calls a model, imports the SDK or changes V2. It also does
not reduce files produced by future V2 runs; direct compact writing is a follow-up.

The output is a dated Israel-local folder containing definitions.json, export.json
and one JSONL per question inside each temperature folder. A full current campaign
has seven folders, ten files per folder, 500 prediction lines per file. SDK default
is separate from explicit 1.0. File sizes depend on response length.

Check export.json: export_status describes conversion, collection_status describes
missing predictions, source_execution_status preserves the original run status.
A successful export can contain a partial experiment or recorded failed calls.
Counts include errors; missing calls are not invented. Source/export sizes and
checksums are recorded. Keep originals until you explicitly choose cleanup after
verification. No cleanup command is included.

## Supported evidence and field mapping

Only generic-question, string inputs, choice/noul and replay mode are supported.
Direct mode and ambiguous temperature-folder mappings fail explicitly. Definitions
are copied from the frozen source manifest after case/suite hash validation.
Optional roles are stored exactly as supplied; analysis must validate their identity.

Inference id becomes inference_id; case/question/config IDs resolve through the
original replay hash convention. Completed becomes success; error stays error.
Raw response and error are preserved in full. Inference_seconds,
baseline_rule_seconds, load_seconds and created_utc go into timing. Availability
is copied. Unknown metadata (including effective_temperature) goes into
source_metadata. Payload and requested_config are removed only after reconstruction
checks, including choice order. External logs and baseline_result are removed.
SDK fields within raw_response, even named logs, remain. Decimal parsing retains
finite numeric values beyond float precision. Missing fields are never synthesized
as zero or probability values. A null payload is supported only for a recorded
error before invocation with no raw response.

V2 has no portable process PID/lock. SOURCE_STOPPED is an explicit user assertion,
not automated liveness detection. The exporter rejects an absent assertion and
checks the manifest, attempts/active metadata, roles and all inference files before
and after copying and immediately before publishing. This detects changes but
cannot prove the process stopped. Stale running status is kept as provenance.

Raw records stream one at a time. Memory additionally holds definitions and compact
planned-ID/seen-ID sets proportional to the grid, never all raw responses. One
prediction file is opened at a time. Temporary destinations are removed on failure;
publication is a same-parent rename after verification. There is no converter resume.

## Offline checks

From repository root: `python -B -m unittest discover -s experiments/tools/checks -v`.
The opt-in `checks/scale_export.py` creates 35,000 temporary synthetic source files,
includes a one-megabyte raw field, exports and checks all 70 partitions, and reports
bytes/time/process peak RSS. Run it separately; it makes no model calls. Its output
is not a size or performance promise for actual SDK responses or Mac hardware.

## Analyze after export

Open `analyze_v2_export.py`, set EXPORT_FOLDER and a new REPORT_FOLDER outside the
export folder, leave STAGE='development', and click Run. Matching ROLES_FILE must
have been included at export. Reports contain only authorized stage cases.
Temperature/policy stages follow the existing research role contract. Final held-out
analysis requires FINALISTS_FILE from the existing frozen-finalists workflow, with
matching identities and native policies; it cannot be used for tuning.

The analyzer requires the production source fingerprint recorded by the original
experiment. If source code changed, use the matching original source checkout;
it refuses to silently evaluate old evidence with different rules. It imports only
native validation/enrichment/rule functions and research role contracts; it never
imports the V2 collector or model loader. Outputs are summary.json and report.md.
Unknown/missing predictions, technical errors, rule rejection and accepted unclear
are counted separately. Coverage uses planned authorized cases, while accuracy and
accepted/actionable errors use only settled labels. Source evidence stays sealed.

Synthetic validation on Linux: 35,000 records, 70 partitions of 500, including one
1MB raw field; source inference bytes 27,892,316 and export bytes 19,660,318;
conversion 8.416 seconds, peak process RSS 72,720 KiB including fixture creation.
These fixture measurements are not estimates of Sharon's actual run. Exporter and
analyzer checks additionally cover long small-fixture responses, payload/choice
order conflicts, errors, partial evidence, role boundaries and native-rule parity.


## Finalist completeness and class support

Final analysis validates every frozen candidate and native policy before evaluating
predictions. Missing or duplicate partitions, absent configurations, changed
settings and excluded frozen rules are structural incompatibilities: analysis
fails without creating a report. Missing inference records inside an otherwise
valid partition remain supported and are counted as missing/partial.

Summary vectors expose `balanced_accuracy_present_classes`, `support`,
`missing_classes` and `comparable_all_classes`. Support counts successfully
evaluated, settled labels only; technical errors, missing records and unsettled
labels are counted separately. `balanced_accuracy` remains a compatibility alias
with the same present-class value. An absent class has no observed recall; it
is not assigned a zero recall. Zero scored cases yield a null average.

Run review regressions from repository root with
`python -B -m unittest discover -s tests -p test_v2_export_review.py -v`.
These tests generate temporary evidence, including a real fixture-worker → export
→ analyzer integration, with model/SDK access blocked. They use no experiment
fixture files and never convert an actual experiment.


Automated experiment checks have been deferred to `tests/deferred/`; see its manifest and coverage report before re-enabling them. Earlier check commands above are historical. Manual experiments and campaign definitions remain available.
