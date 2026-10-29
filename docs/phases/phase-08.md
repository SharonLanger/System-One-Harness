# Phase 08 — lexical file references

Objective: extract ordered mentions with an external regex, without reading files
or inferring read intent. Starting published commit: a1f3339 (Phase07).
Environment: Python3.12.14 / pytest9.2.0; Linux; SDK/model/harness not used.

Independent test planner: /root/source_builder/phase_reviews (gpt-6-luna/medium).
Plan preceded implementation: paths/delimiters/suffixes, duplicate ordering,
lexical classes, custom expression validation, complete space captures, malformed
captures, unsupported Windows paths, and filesystem guards.

Contract: explicit regex with named `path` captures the complete path excluding
quotes and line suffixes. Frozen results preserve path, basename, kind, and exact
capture offsets. Space syntax is expression-owned; no default guessing regex.
Classification is case-sensitive, declaration before test before production.
No reads, normalization, resolution, model calls, or intent inference.

Tests: new tests/test_file_reference_utils.py. Expected outputs manually specified
from fixture strings and capture spans; no existing tests/fixtures changed.
Baseline: python -m pytest -q: 163 passed. Expected TDD red: new test collection
failed because file_reference_utils module did not exist. Full candidate suite:
189 passed, 0 failed, 0 skipped. Independent final verification: same reviewer
independently inspected requirement/source/tests/diff and reran the complete suite:189
passed, 0 failed, 0 skipped. git diff --check clean.

Execution mode: mocked SDK boundary in inherited tests; detector has no inference.
Real Laya compatibility remains deferred to Phase20. Regex owners must capture
complete references; Windows/backslash/control-character captures reject explicitly.
Verifier verdict: VERIFIED for stated Phase08 scope. Decision: COMPLETE.
No blockers; unchanged inherited mock tests preserve model/settings routing and
JSON/enrichment/rules/extraction coverage. No new model/settings combinations.
Evidence timestamp: 2026-10-29; candidate is the focused Phase08 diff from a1f3339.
