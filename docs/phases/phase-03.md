# Phase 03 — typed JSON questions

Starting commit c14a102; baseline `python -m pytest -q`: 29 passed.
Python3.12.14/pytest9.2.0. Independent planner/verifier: phase01_plan (Luna).
Plan: literal payloads and roundtrips for three types, name outside SDK body,
ordered criteria, single/list inputs, malformed/missing files, duplicates/invalid
criteria rejected, mutable instance isolation and inline-vs-JSON SDK parity.
Expected fixture department=billing and exact SDK payload come from the captured
pair. Original question constructors and serializers ground valid-input semantics;
no evaluate methods copied. Empty list retains original `{}` loader behavior.

Test-first run: absent questions/models.py caused 1 expected collection error.
Files: questions/models.py, load.py, test_questions.py; docs. No prior tests changed.
Raw JSON-loaded request follows the same adapter. All calls mocked, no live SDK,
weights or service use. Enrichment/rules/extraction deferred. SDK/revision unknown.
Full suite `python -m pytest -q`: 48 passed, 0 failed, 0 skipped. Initial test syntax emitted a pytest9 iterator-parametrize deprecation; Astra/high repairs converted zip to list(zip), retaining all cases. Implementer and repair-agent clean full reruns: 48 passed, no warnings. Independent final phase01_plan inspection and full rerun: 48 passed, 0 failed, 0 skipped, no warnings. Verdict: VERIFIED for stated Phase03 scope.
Real compatibility deferred Phase20. Candidate reviewed date:2026-10-29.
Decision: COMPLETE.
