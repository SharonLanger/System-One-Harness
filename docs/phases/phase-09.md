# Phase 09 — bounded production TypeScript resolution

Objective: exact-path-first resolution with deterministic basename fallback.
Starting published commit: c15add6 (Phase08); clean. Python3.12.14/pytest9.2.0.
Independent planner: /root/source_builder/phase_reviews (gpt-6-luna/medium),
plan delivered before tests/implementation. Independent final verifier: same agent.

Plan: nested cwd; exact relative/absolute precedence even with duplicate basenames;
unique/ambiguous/missing basenames; explicit path never falls back; directory,
excluded test/declaration/non-TS, traversal/symlink escape; Unicode/spaces;
permission/scanning failures, stable candidates, unchanged temp repository.
Expected results hand specified from temporary fixtures, never user source.

API: resolve_file(reference, cwd=..., repository_root=...) accepts a string or
FileReference. Resolution holds status, selected_path or None, and sorted canonical
absolute candidate Paths. Only case-sensitive production `.ts` eligible. Excluded
mentions stop before lookup. Exact in-root regular files win; missing basename-only
references may scan. Explicit paths never fallback. Symlink directories, .git, and
node_modules excluded from scanning; canonical targets must stay in root and be eligible production TypeScript. Any scan
failure prevents selection to avoid an unseen duplicate. cwd/root must exist and
cwd must be inside root. No source content reads or writes.

Baseline full suite: 189 passed. Expected TDD red: missing resolve_file module
(test collection failed). Initial full candidate:205 passed. Inspection found
canonical symlink targets needed the same production eligibility filter as mentions;
heavy diagnostic/fix agent: /root/source_builder/source_repairs (gpt-6-astra/high).
Repair TDD:10 expected regression failures before fix (17 other resolver tests
passed); canonical target eligibility now checked for exact paths and scan results.
Added11 regressions including valid symlink deduplication. Implementer reran full
suite after repair:216 passed,0 failed,0 skipped.

No existing test expectations or fixtures changed. Implementation:
building_blocks/resolve_file.py; tests/test_resolve_file.py; README/progress/record.
Execution mode: inherited SDK calls mocked; resolver uses only real local filesystem
operations in disposable fixture directories. No SDK/harness used, no real calls.
New model/settings combinations: none; inherited routing and raw/enrich/rules/answer
regressions retained. Live identity/settings remain unverified until Phase20.

Independent final reviewer inspected actual source/tests/diff and requirement
mapping, then independently reran python -m pytest -q:216 passed,0 failed,0 skipped.
git diff --check clean. No blockers; symlink repair verified.
Verifier verdict: VERIFIED for Phase09 scope. Decision: COMPLETE. Evidence date:2026-10-29.
Limitations: TS-only production files; no test/declaration extraction; basename
scan skips vendor/VCS and symlink directories. Permission errors are controlled
monkeypatch fixtures because root permissions would obscure chmod-only tests.
