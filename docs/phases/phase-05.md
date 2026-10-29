# Phase 05 — inner answer policies

Starting commit0e85e25 (published Phase04). Baseline `python -m pytest -q`:85 passed.
Environment Python3.12.14/pytest9.2.0. Independent planner/verifier: phase01_plan.
Plan: every operator below/at/above threshold; nested lookup; universal+type AND
in order; absent type/empty conditions; first failure; legacy upper-bound reason;
missing/null/eqNone semantics; malformed policy containers and tuple unpacking.
Expected literal booleans/reasons grounded in original OPS/resolve_field/rules.py.
Test-first absent conditions module gave1 expected collection error.

Files: answers/conditions.py, rules.py, test_rules.py; docs. Inner policy objects
only; canonical outer envelope remains Phase07. Valid source semantics retained.
Missing and explicit null both resolve to None: eqNone accepts both; failing other
operators report field_missing. Failed upper bounds still report below_threshold.
This is a legacy reason name, not a direction description. Callers unpack tuples.
New config boundary rejects malformed containers/paths/types and nonfinite values.
No old runner/evaluator framework imported. No prior tests or expectations changed.

Full suite `python -m pytest -q`: initial115 passed; proactive malformed-list/dict operator bug escalated to Astra/high repairs. Eight new regressions reproduced TypeError; string guard fixes intended ValueError. Full final implementer/repair reruns:123 passed,0 failed,0 skipped. Mock-only; no model/settings changes or
SDK calls. Fixture capture versions remain unknown. JSON ingestion unchanged;
enrichment tested previously; answer mapping comes next. Live compatibility remains
Phase20. Independent phase01_plan full candidate inspection and rerun:123 passed,0 failed,0 skipped. All source operator/null/reason semantics and repair regressions verified. Review date2026-10-29. Verdict:VERIFIED for stated Phase05 scope. Decision:COMPLETE.
