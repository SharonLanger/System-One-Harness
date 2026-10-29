# Phase 01 — lazy adapter

Starting commit: 8711f27. Python 3.12.14, pytest 9.2.0. No prior project tests existed;
this is an absent baseline, not an empty-suite pass. No AGENTS.md in ancestors.
Independent test planner: phase01_plan (gpt-6-luna, medium). Independent final
verification: phase01_plan (separate Luna agent). The planner specified exact default SDK arguments, raw
preservation, strict JSON, malformed response/errors, explicit mock mode, isolation,
portable import and same-adapter example. Tests were written first: collection
failed on the absent adapter (1 collection error), then implementation was added.

Scope: default one-question adapter; lazy explicit real path; supplied complete
captured fixture and derived single-choice subset, with provenance. Tests assert
captured department=billing and exact fixture values; fruit example is synthetic.
No previous tests changed. Files: package adapter, setup, fixtures, tests, example,
README and these docs. See fixtures README for unknown SDK/revision and model label
limitations. Temperature and registry coverage belongs to Phase 02.

Full-suite command: `python -m pytest -q`. Candidate result: 19 passed, 0 failed, 0 skipped; independently rerun: 19 passed.
Execution mode: injected mocked SDK boundary only. No SDK installed or imported.
Requested model default and explicit fixture checkpoint are request routing, not
observed model identity. JSON preserves the raw response; no enrichment/rules/
extraction introduced. Live compatibility deferred until Phase 20.

Independent findings: full candidate inspection and independent full-suite rerun found no blockers. Fixture provenance and strict initial choice shape verified. Candidate reviewed 2026-10-29 before commit. Verdict: VERIFIED for stated Phase 01 scope. Decision: COMPLETE.
