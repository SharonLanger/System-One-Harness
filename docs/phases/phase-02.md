# Phase 02 — invocation settings and reuse

Starting commit: e7d4123. Baseline: 19 passed. Python3.12.14/pytest9.2.0.
Independent planner/verifier: phase01_plan (separate Luna agent).
Plan: source-faithful default/explicit config serialization and SDK args;
A/B/A, T1/T2/T1, language, None vs zero, immutable keys, failures/recovery,
separate registry lifetimes and raw JSON preservation. Expected args from original
config.py/engine.py, not generated from implementation. Test-first absent config
module caused the expected single collection error. No existing tests changed.

Files: laya/config.py, registry.py, adapter integration, test_config.py.
One invocation owns a registry keyed by model, temperature and language. No globals.
Config is immutable; invalid/nonfinite config rejected. Explicit zero is only a
forwarding/cache test, not live support. Failed loads are not cached. Exact default
predict omits lang even for configured language when temperature is None, preserving
source behavior. Simulated identity is Python object identity, not real model metadata.
Full suite: `python -m pytest -q`; initial candidate: 28 passed, 0 failed, 0 skipped; independent rerun: 28 passed. Independent reviewer identified missing subprocess lifetime coverage. Escalated to repairs (gpt-6-astra/high) for the narrow test repair; Astra added an isolated two-process regression without changing existing tests or production code. Implementer and repair-agent full reruns: 29 passed, 0 failed, 0 skipped. Final independent phase01_plan rerun: 29 passed, 0 failed, 0 skipped. Full final candidate inspected 2026-10-29, including the process regression. Verdict: VERIFIED for stated Phase02 scope.
Execution: mocked SDK only; A/B/A, 0.2/0.7/0.2, None/0, en/fr. JSON raw unchanged;
enrichment/rules/extraction not yet added. SDK and model revisions unknown; live
compatibility deferred Phase20. No previously declared test expectations altered.
Decision: COMPLETE.
