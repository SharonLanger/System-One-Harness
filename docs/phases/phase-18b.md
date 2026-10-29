# Phase 18B — same-file context through flow and hook

Starting revision: Phase18A. Independent test planning and a separate design
review preceded implementation. Independent final verification is complete.

The flow now retrieves the validated same-file semantic bundle after accepted
method selection. Selected ID, path/hash, callable map and repository confinement
checks remain. The original model input stays prompt plus signature questions;
collected source does not enter selection or fallback questions. Existing exact
extraction remains available as a separate API.

Flow `max_dependency_depth=2` permits0–20; `max_dependency_chars=12000` permits
1–1,000,000 UTF16 units. Invalid values, including booleans/floats, no-op with
`invalid_dependency_budget` before source/model work. Hook flags
`--max-dependency-depth` and `--max-dependency-chars` pass these values to the
flow and validate before SDK loading. The collection budget counts complete
dependency source only, excluding selected code and metadata.

Three budgets remain distinct: model question input uses Unicode characters in
prompt/questions; dependency collection uses UTF16 source units; final hook
additionalContext uses Unicode characters in the header plus compact JSON,
including selected/display code, dependencies, provenance and gaps. Final ceiling
remains8,000 (lower with `--max-context-chars`). Oversize returns the documented
empty-stdout no-op; no truncation or automatic reduced-context retry occurs.
Explicit source-budget omission can still deliver complete selected code with
partial coverage and a size/depth gap.

Tests use actual helper/bridge/flow/hook components and a fixed simulated SDK
boundary. Manually specified const/helper source verifies dependencies, CRLF,
astral provenance, deterministic whole-unit omissions, depth0/1/20 and upper
source budgets. Selection requests are checked unchanged and signature-only.
Invalid flow limits assert zero source/model work. Hook scenarios cover a9,000
character dependency causing final overflow, a32-unit collection limit omitting
it with a gap, non-BMP UTF16 source exact/one-short limits, and complete-render
exact/one-short boundaries. Earlier source-stale/malformed, native stdout,
selection/fallback and hook scenarios remain in the accumulated suites.

Tests-first:16 new behavior cases failed before integration;5 invalid-flag no-op
cases already passed via argparse rejection. Existing hook expected-context
construction now uses the collector. The old no-dependency limitation assertion
for a simple fixture is promoted to empty dependency list plus explicit same-file
semantic limitation; malformed-helper monkeypatch targets the new collector.
No regression scenario was removed.

Environment: Python3.12.14/pytest9.2.0, Node24.22.1/TypeScript5.9.3.
Baseline: fresh build/typecheck, Node26/26 and Python374/374 passed87.85s,
zero failures/skips/xfail. Focused flow/hook gate:109/109 passed81.33s.
Final implementer gate: fresh build/typecheck, Node26/26 and Python395/395
passed108.49s, zero failures/skips/xfail; git diff --check clean. Independent
verification reviewed the complete diff and outgoing documents, then reran a
fresh build/typecheck, Node26/26 and Python395/395 in102.12s, zero failures/skips/
xfail; git diff --check clean. README wording was clarified; no blocker remains.
Evidence date:2026-10-29. Synthetic fixtures; SDK boundary mocked throughout.
No actual model/SDK/Claude execution or activation. Cross-file collection remains
Phase19; real compatibility remains deferred until20. Mutable state, closures,
module effects, dynamic targets and universal context sufficiency remain partial.
Verifier verdict: VERIFIED for Phase18 same-file collection and flow/hook scope.
Decision: COMPLETE for Phase18.
