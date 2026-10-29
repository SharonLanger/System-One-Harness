# Phase 16 — complete isolated hook scenarios

Starting commit: fac696fa3ddca2e1aa477dacf2705ba396d1f5ee. Same Python 3.12,
Node 24 and pinned TypeScript 5.9.3 environment. Independent planner/reviewer:
`/root/flow_builder/phase_reviews` (Luna medium). Baseline serialized fresh
build/typecheck +6 Node +336 Python passed (61.58s Python); no skips/xfail.

Scope: subprocess scenario tests, one small standalone example, future manual
project-local enable/disable recipe and complete continuation handoff. No runtime
hook/flow/adapter source changed. Only SDK boundary is simulated; actual package,
question construction, JSON validation, enrichment, named policies, flow, Node
helper, extraction and protocol serialization run.

Independent test plan: tracked fixture source-to-context through real Bash/Python
hook, exact full request/response/output; explicit rejected response through real
policy; unmatched, model/extractor failures; independent lifetimes and different
choices without cache bleed; immutable tracked source; isolated example; documented
settings parsed and command tested with fake SDK, never activated.

TDD: 9 new scenario cases first produced 2 expected failures (example/recipe absent)
and 7 passes for behavior already implemented. Added the example and recipe;
focused 9/9 passed (15.94s). No existing tests/fixtures/oracles altered. Two tracked
basic.ts callables selected by distinct explicit responses in separate processes
with same simulated model mock-hook(.2/fr); each loads own agent and returns only
expected source. Output matches independent extraction/provenance expectation,
stdout JSON only, SDK noise stderr. Request fixture bytes and tracked source
bytes preserved. Rejected/abstained/malformed/model exceptions safe no-op; deliberate
concurrent edit occurs only in disposable source by mock boundary, real stale-ID
extraction refuses context. Example uses mock-scenario/default settings, real
parser/flow, explicit fake load/predict and fixed synthetic raw response. No answer
inferred by fake from prompt; no real model metadata inferred from requested IDs.

Recipe is documentation only; tests execute its exact shell command with fake
SDK, then without --real, verify output/no-op and no .claude directory created.
No Claude command/session/global configuration is invoked or written. Removing a
future entry is described, actual Claude reload/delivery/disable remains unverified.
Official unversioned hooks reference was verified in 15 on 2026-10-29. No SDK version
or actual harness version available; all model calls explicitly simulated.

Implementation files: examples/user_prompt_submit_scenario.py,
tests/test_hook_scenarios.py, docs/hook-usage.md, README/progress and continuation.
Final commands: npm --prefix typescript-helper run build; npm --prefix
typescript-helper test; python -m pytest -q (all accumulated tests).
Final implementer serialized fresh build/typecheck +6 Node +345 Python passed
(75.52s Python), zero skips/xfail. Independent final serialized fresh build/typecheck +6 Node +345 Python passed
(72.10s Python), zero skips/xfail. Reviewer inspected the complete actual diff,
scenario assertions, recipe and continuation. Verdict: VERIFIED for stated
Phase16 mock/subprocess scope. Decision: COMPLETE. Candidate evidence2026-10-29. Real Laya compatibility remains blocked
until Phase20 (Linux x86_64, MLX/laya_mlx absent; no install/import/load/inference).
Context remains partial and callable support intentionally narrow until 17–19.
