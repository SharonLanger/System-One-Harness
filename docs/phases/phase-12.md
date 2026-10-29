# Phase 12 — dynamic method-selection block

Objective: select from real source candidates through shared prediction machinery.
Starting published commit:364d56d (Phase11), clean. Baseline fresh build/typecheck,
6 Node and243 Python tests passed. Python3.12.14/pytest9.2.0, Node24.22.1,
TypeScript5.9.3. Independent planner/final reviewer:
/root/source_builder/phase_reviews (gpt-6-luna/medium); plan before implementation.

Plan: exact dynamic criteria, named policies, four-file contract, no-candidate no
load, duplicate names/distinct IDs, selected range/code, no-match sentinel, noise,
multiple relevant, policy rejection, unknown-ID failure; template/input immutability;
candidate/input budgets below/at/above; exact settings and shared pipeline.
Manual expectations use synthetic raw choice/noul responses; only SDK is mocked.
Actual Node outline and extraction execute for candidate/range fidelity. No captured
fixture changes, no previous tests weakened. Original working method definition
was not recovered (source inventory has no method question JSON); new baseline
explicitly documented, no formatting or accuracy parity claimed.

Contracts: `method_selection.block.run(text, source_outline, config=...,registry=...)`
returns selected_id/reason/decisions/candidate_map. Criteria map opaque IDs to
signatures plus none_or_unclear. Only accepted method ID and accepted
multiple_relevant=no select. Accepted sentinel and multi=yes remain no-ops;
policy rejection preserves named decision reasons. Unknown IDs fail validation.
Candidate map keeps path/hash/ranges outside model payload. Budgets default64
candidates/16000 Unicode characters (text + compact question JSON), not tokens;
overflow returns explicit no-op before load without truncation.
QuestionBlock.run adds optional question_payloads with exact names, Question
validation/copy; default remains identical and shared predict/interpret execute.

TDD red: missing method_selection module during new test collection. Initial
candidate:6 Node passed, Python250 passed/1 failed because a new negative test
constructed AgentRegistry without mandatory explicit loader before testing input
validation. Heavy diagnosis/repair assigned /root/source_builder/source_repairs
(gpt-6-astra/high); assertions unchanged. Repair supplies a fail-if-called loader only in that test.
Heavy agent and implementer each ran fresh build/typecheck + complete suites:
6 Node and251 Python tests passed,0 failed/skipped; diff check clean.
Initial independent review verified6 Node/251 Python tests. Root requested
installed-wheel resource proof before commit: added test_packaged_blocks.py, which
builds wheel, checks both blocks four resource bytes, extracts to isolated target,
and loads both QuestionBlocks in a subprocess with only installed PYTHONPATH.
This documents existing package_data behavior (passed immediately), not a new
implementation TDD red. Final implementer build/typecheck +6 Node +252 Python
passed,0 failed/skipped. Independent final reviewer inspected added wheel test/evidence and independently
reran build/typecheck, all6 Node and252 Python tests,0 failed/skipped; diffcheck clean.
No blockers; requirements including installed resources verified.

Execution: mocked Laya model mock-selection, explicit temperature0.2/langfr exact
load/predict args verified; agents are controlled fixture objects. No live SDK or
model identity/settings observations, weights, model imports or inference. Inherited
JSON/enrichment/rules/interpreter regressions preserved. Harness unused; real
compatibility deferred to Phase20. Files: method-selection four files, shared
block dynamic override, tests, README/progress/record. Evidence date:2026-10-29.
Known limits: signatures only, provisional policy, no method accuracy measurement,
initial top-level callable subset and no dependencies. Full verification complete.
Verifier verdict:VERIFIED for Phase12 scope. Decision:COMPLETE.
