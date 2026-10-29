# Phase 10 — compiler outline and Python bridge

Objective: real parser-backed outlines through a bounded JSON subprocess protocol.
Starting commit:b8ebcc1 (published Phase09), clean; baseline216 passed.
Independent planner: /root/source_builder/phase_reviews (gpt-6-luna/medium),
plan delivered before implementation. Independent final verifier: same agent.

Scope: ordinary named top-level function implementations only. Classes/methods,
arrow/function expressions, nested functions, async/generator/overload forms emit
unsupported_callable diagnostics. No source imports, transpilation, or execution.
Protocol: stdin {action:"outline",path}; success one JSON object stdout; errors
stderr + nonzero. Schema1 contains canonical path, SHA256 of decoded UTF8 source,
source-order candidates with source-bound IDs, raw signatures, UTF16 ranges and
1-based line/column; diagnostics and explicit limitations. Parser errors fail
rather than trusting a recovery outline. Exact code retrieval deferred to11.

Pinned dependencies: TypeScript5.9.3, @types/node24.10.1 and lockfile. Node24.22.1,
npm11.9.0; Python3.12.14/pytest9.2.0. Official compiler API documentation checked
2026-10-29: https://github.com/microsoft/TypeScript/wiki/Using-the-Compiler-API
(createSourceFile/forEachChild/location API; pre7 API compatible pinned compiler).

Independent tests cover signatures/UTF16 locations, empty/parser errors, explicit
unsupported forms, comments/strings, spaces, source side effects never executed,
actual Python-to-Node CLI, missing Node/build, nonzero/stderr, malformed JSON/schema,
array argv, bounded timeout. Expected outputs hand specified from synthetic source;
no existing fixture/test changes. Source fixture is purpose-built, not private code.
Expected reds: missing Python bridge module and missing helper build (Node test
failed with MODULE_NOT_FOUND). npm install pinned3 packages succeeded; initial
build/typecheck +4 Node tests +226 Python tests passed before additional schema and
timeout-boundary tests. Final fresh npm ci (3 packages), build/typecheck, entire Node suite:4 passed,
0 failed/skipped; python -m pytest -q:237 passed,0 failed/skipped.
Independent reviewer reread actual source/tests/diff and independently ran fresh
npm ci, build/typecheck, all4 Node tests and all237 Python tests;0 failed/skipped.
Requirement mapping confirmed; no blockers. git diff --check clean.

Python default helper assumes source checkout. Installed applications must pass
an explicit built helper path; no wheel-bundled compiler/build claim. subprocess
uses argv, explicit UTF8, captured channels, timeout<=60sec (default5). No shell.
No broad callable or dependency completeness claimed.

Execution mode: all Laya calls inherited mocks; helper and bridge execute real
local parser code. SDK/harness versions not applicable; no model imports/loads,
weights, or inference. No new model/settings combinations. Raw/enrichment/rules/
interpretation regressions retained; live compatibility deferred to Phase20.
Implementation: typescript-helper package/source/tests; Python bridge + tests;
fixture; .gitignore; README/progress/record. Evidence date:2026-10-29.
Verifier verdict:VERIFIED for Phase10 scope. Decision:COMPLETE.
