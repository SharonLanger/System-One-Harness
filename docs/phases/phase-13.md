# Phase 13 — first offline file-method context flow

Objective: ordinary Python detection→resolution→outline→selection→exact code.
Starting published commit:6292277 (Phase12), clean. Baseline fresh build/typecheck,
6 Node +252 Python tests passed. Independent planner/final reviewer:
/root/source_builder/phase_reviews (gpt-6-luna/medium); plan before implementation.
Python3.12.14/pytest9.2.0; Node24.22.1; TypeScript5.9.3. SDK/harness unused.

Eligibility is deliberately narrow: case-insensitive Explain, one backtick-quoted
production `.ts` path, colon, nonempty explanation question. Exactly one lexical
file mention must equal that target; configurable external regex remains accepted.
Filename alone, output-only request and incidental log do not prove intent. General
role classification and broader prompt formats remain later work.

Flow API run(prompt, cwd=..., repository_root=..., config=..., registry=...) uses
real detector/resolver/compiler outline/method block/compiler extraction. Source
path confinement rechecked before outline/extraction. Returned path/hash/callable
must match selected source map. Context envelope:status=context,reason=None,
context exact raw source/provenance plus coverage=partial. No-op envelope always
status=noop,reason=<explicit reason>,context=None. Resolution/helper/model failures,
policy rejection, abstention, ambiguity and budgets fail closed. No source writes.

Independent tests cover actual spaced relative/absolute paths, exact SDK request
and config, unchanged prompt/source; no file, multiple files including plain second
path, ambiguous basename, missing/test/declaration/non-TS, output/log, unsupported
syntax, outside traversal/symlink, parser/malformed outline/extraction, rejected/
abstained selection, model error/stale source, custom regex, budgets/missing build,
and a direct example subprocess. Actual source integration mocks only Laya SDK;
malformed-output boundary tests separately use synthetic helper/stub responses.
Expected code and outcomes manually specified. Existing tests/fixtures unchanged.

Expected TDD red: new flow package missing at collection. Final implementer:
npm --prefix typescript-helper run build (typecheck passes);
npm --prefix typescript-helper test:6 passed,0 failed/skipped;
python -m pytest -q:272 passed,0 failed/skipped. This includes installed-wheel
resources for both blocks and all original model/settings/JSON/enrichment/rules/
extraction tests. Offline example exercised by subprocess test.
Independent Luna reviewer reread actual source/tests/diff and entire continuation;
requirement mapping confirmed, no blockers. Independently reran build/typecheck,
all6 Node and272 Python tests:0 failed/skipped; diffcheck clean. Continuation handoff updated within this phase
before commit to document exact APIs, demo/validation commands and remaining14–19.

Mock settings: controlled mock-selection with temperature0.2/langfr; direct demo
uses explicit mock loader with RunConfig defaults. Requested settings checked at
fake boundary, not observed live metadata. No model weights/imports/inference or
harness activation. Real compatibility remains blocked/deferred to Phase20.
No method-selection accuracy or universal dependency sufficiency claim.
Files: flow package, direct example, tests, README/progress/continuation/record.
Candidate is focused Phase13 diff from6292277; evidence date2026-10-29.
Verifier verdict:VERIFIED for Phase13 scope. Decision:COMPLETE.
