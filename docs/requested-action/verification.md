# Requested-action verification

PR #19 is implemented on its existing branch, per Sharon's explicit instruction.
The original plan is retained. No merge is performed.

## Baseline and reviewed deviations

Remote baseline: PR19 head `5ba40e173fe5c5ec6717cfbc815b4ed1b53da590`,
parent main `6de4c8eb9691b0594b12bf5cbf2fa67c862b59ad`.
Reconstructed source tree verified exactly as
`12f5fab22f5b2f775db658d0f10bbffc1bdc1f30` before changes.
Python 3.12.14, Node v24.22.1, npm 11.9.0.

Astra reviewed two setup deviations:

1. CLI GitHub credentials were unavailable. Use connector-backed pinned-tree
   reconstruction and a leased fast-forward update of PR19's existing branch.
   Local files were reused only after blob-SHA verification. The remote branch
   update must expect the original head and preserve concurrent changes.
2. Initial relevant baseline: 149 passed, 14 failed, all reporting the missing
   `build/typescript/cli.js`. Build the helper before rerunning the baseline.
   Reused dependencies matched the lockfile SHA-256
   `39df3981879a4d62b300d4462a593b5983efe34b8b3b07999ab8751f58de520f`:
   TypeScript 5.9.3, @types/node 24.10.1, undici-types 7.16.0.
   Build outputs were generated from this checkout.

Astra approved both adaptations without product or shared-runtime changes.
User authorization supersedes separate implementation PR and document removal.

## Executed verification

- Initial new tests: 30 failures before implementation (29 missing new module,
  one missing new fixture); no model loaded. Fixtures were then added explicitly.
  T25 and T30 were added after implementation, so the planned test-first sequence
  was not fully followed. Their final passing tests establish behavior, not prior
  red evidence. Astra reviewed and recommended honest disclosure; a retrospective
  missing-module run would not repair chronological evidence.
- Built helper: `npm --prefix typescript-helper run build`, passed.
- TypeScript: `npm --prefix typescript-helper test`, 137 passed, 0 skipped/failed.
- Relevant baseline after build: `python -m pytest -q tests/block_runtime
  tests/test_packaged_blocks.py tests/test_v2_blocks.py
  tests/test_v2_flow_composition.py`, 163 passed.
- New-block suite: `python -m pytest -q tests/test_requested_action*.py`,
  64 passed before independent review.
- Full suite: `python -m pytest -q`, 1,132 passed, 3 existing skips in
  219.02s. This run collected the initial 64 new tests; the two verifier-driven
  additions were then covered in the final 66-test suite (all passed).
- Final new-block suite after verifier/data/doc updates: 66 passed in 1.05s.
- `git diff --check` passed; no existing tests were weakened.

Synthetic SDK responses exercise the real catalog, response validator, enrichment,
rule evaluator, extraction and runtime. No real SDK inference/download was run.
Wheel tests build and extract into a separate directory, launch Python outside
checkout with only installed resources on PYTHONPATH and verify package origin.
No existing production module, old test, hook, flow, experiment or shared rule is
changed. Production changes are only the new block and its own named defaults.

## T01–T46 evidence map

Names refer to tests/test_requested_action_*.py unless an existing suite is named.
Parameterized functions cover each variation in their decorators.

| ID | Concrete evidence |
| --- | --- |
| T01 | block: test_T01_T07_T10_T13_T43_labels_and_caller; test_T01_saved_fixtures |
| T02 | block: test_T02_T03_T04_transport_only_no_token_claim |
| T03 | block: transport test and test_T03_T05_T06_T42_input_rejected_before_load |
| T04 | block: transport test Unicode, Hebrew, filename case |
| T05 | block: input_rejected_before_load parameters |
| T06 | block: input_rejected_before_load extra code/implementation parameters |
| T07 | block: labels_and_caller compares captured payload to real Catalog |
| T08 | integration: test_T08_T44_fresh_import_and_block_construction guards loader during real Block construction |
| T09 | block: test_T08_T09_T11_T12_T21_T22 wraps actual enrichment |
| T10 | block: labels_and_caller; test_T10_invalid_output; contract: test_T34_skip_and_T10_reducer_validation |
| T11 | block: test_T08_T09_T11_T12_T21_T22; contract: test_T23_T24_rules_same_response |
| T12 | block: test_T08_T09_T11_T12_T21_T22 metadata in real enrichment input |
| T13 | block: labels_and_caller and test_T14_T20_T43_policy_boundaries |
| T14 | block: policy_boundaries .49/.30/.21 |
| T15 | block: policy_boundaries .55/.45/.00 |
| T16 | block: policy_boundaries .50/.35/.15 |
| T17 | block: policy_boundaries .499/.300/.201 and .500/.351/.149 |
| T18 | block: policy_boundaries .50/.50/.00 |
| T19 | block: policy_boundaries asserts completed/undecided |
| T20 | block: policy_boundaries compares real accepts reason, null top reason |
| T21 | block: test_T08_T09_T11_T12_T21_T22 missing answer_confidence |
| T22 | block: test_T08_T09_T11_T12_T21_T22 zero unrelated metrics |
| T23 | contract: test_T23_T24_rules_same_response |
| T24 | contract: test_T23_T24_rules_same_response default preservation |
| T25 | contract: test_T25_T26_T29_T30_T31_invalid_overrides; integration: test_T41_T42_logs |
| T26 | contract: invalid_overrides missing refs/unknown keys |
| T27 | contract: test_T27_T28_T32_T35_question_customization_and_order |
| T28 | contract: question_customization_and_order injected Catalog reference |
| T29 | contract: invalid_overrides type change |
| T30 | contract: invalid_overrides added/missing/renamed labels |
| T31 | contract: invalid_overrides list criteria/numeric description |
| T32 | contract: question_customization_and_order explicit custom text |
| T33 | contract: test_T33_bad_preparation keys/type/labels/blank |
| T34 | contract: test_T34_skip_and_T10_reducer_validation |
| T35 | contract: question_customization_and_order reversed criteria |
| T36 | contract: test_T36_invalid_raw eight invalid-envelope parameters |
| T37 | contract: test_T37_T40_errors_once_and_failed_load_not_cached |
| T38 | contract: test_T38_T39_T40_registry_config_isolation |
| T39 | contract: registry_config_isolation model/temp/language forwarding |
| T40 | contract: registry_config_isolation and errors_once_and_failed_load_not_cached |
| T41 | integration: test_T41_T42_logs actual JSONL events |
| T42 | integration: test_T41_T42_logs invalid-input/mismatch logs, no prediction |
| T43 | integration: test_T43_caller_branches_all_results explicitly routes all four outcomes |
| T44 | integration: test_T44_no_target_reads_or_utilities and test_T08_T44_fresh_import_and_block_construction |
| T45 | integration: test_T45_installed_wheel; existing tests/block_runtime/test_wheel.py |
| T46 | existing full suite, including test_v2_blocks.py, test_v2_flow_composition.py, test_packaged_blocks.py and tests/block_runtime/ |

## Manual semantic evaluation

E01–E22 are in tests/fixtures/requested_action_prompts.json. They include settled,
provisional and taxonomy_pending status, explicit accuracy eligibility and held-out
cases. No live result exists. Keep held-out cases out of question/rule tuning.
Review unresolved meanings with Sharon before scoring them as accuracy targets.

On the Mac, invoke run with an explicitly real AgentRegistry and the selected
RunConfig; record requested and verified loaded identity separately, SDK/revision,
question/rule, raw/enriched response, expected status/label, decision reason, and
verified truncation diagnostics if available. Count wrong accepted labels and
abstentions separately. This PR includes no additional runner or automatic hook
integration. Prompt transport is unchanged; token fitting/truncation is unverified.

## Independent review

A separate verifier inspected the complete plan, source diff, fixture validity and
T01–T46 mapping, and independently ran the initial new suite (64 passed in 1.04s).
It found no production defect and identified coverage gaps for T08, T43 and T44.
Those were closed with actual Block construction and fresh-process import guards
and an explicit four-way caller routing assertion. The verifier independently
reran the affected integration tests: 6 passed in 0.94s, including installed-wheel
execution. Follow-up review found no remaining blocking implementation/coverage
issues, conditional on full-suite completion. Final new suite: 66 passed in 1.05s.

Existing skips are unchanged: two legacy duplicate-key loader cases deferred for
V1, and one concurrent outside-project symlink replacement case outside V1 scope.
No new test is skipped.
