# RV2 implementation verification

Implementation delivered for review on PR #21. The PR is not merged. Actual browser interaction acceptance is OPEN; live MLX compatibility remains the planned Mac-only check. Do not interpret offline success as model accuracy evidence or full plan acceptance.

## Source and scope

Original PR head: 27acc84c590535a2593cf0dab945f0bbd2e3c5a9. Integrated main: e4faa703d1572a88662e33f2bf8b53f339a5c8aa (merged PR #19). Retrieval used the GitHub connector at exact SHAs because local cloning had no credentials. All 76 production source files were compared using Git blob hashes and match main exactly. Final feature commit uses main's tree plus batch_v2 files and parents original PR head and main. Only batch_v2 is changed relative to main.

## Delivered requirements

- Strict cases/suite validation, immutable question types and canonical labels, wording/choice-description invariants, named rules/configurations, baseline/exclusions, metadata isolation and no repetitions: schema.py + schema tests.
- Generic question path and actual requested-action/context-scope adapters: engine.execute and production runtime contracts.
- Sequential configuration workers, cached agent within worker, offline-only local model resolution, direct and replay execution, no hidden retries or warm-up: engine.worker.
- Atomic inference/case checkpoints, interruption preservation, missing-case resume from existing inference, frozen hashes and hard worker timeout/call/time limits: engine and engine tests. A process killed during prediction is counted as an attempted call, never silently retried as part of that same active step.
- Manifest freezes authored inputs, runtime/source/model fingerprints, requested settings, counts and provenance. Effective SDK settings/tokens are unavailable and explicitly null with explanations. Raw SDK payload/response and production enriched fields/decisions are preserved.
- Results JSONL, summary CSV, per-vector JSON, Markdown and standalone HTML. Four-cell accounting with explicit denominators, technical statuses, operational unscored behavior, noise/tag/split groups, confusion counts and raw evidence links: reporting.py + report tests.
- Required 2×2×2×3 fixture produces 8 vectors, 24 completed logical outcomes and 12 shared synthetic inference records; all four AC/AW/RC/RW outcomes occur. Frozen expected-summary.json is checked against generated summaries.
- README and input-authoring guide provide setup, full JSON files, annotation policy, commands, outputs and manual browser verification.

## Executed checks

From repository root:

```bash
python -B -m unittest discover -s experiments/batch_v2/checks -v
```

Result: 16 tests passed, including 24 parameterized replay-contract scenarios across generic choice/noul and both choice block adapters. Tests cover malformed/missing SDK responses, threshold rounding, evidence immutability, direct/replay parity, counts, four cells, subgroup overlap, label status, actual block input validation, raw-checkpoint resume, no duplicate calls, resume mismatch, exclusions, empty datasets, partial collection, safe HTML escaping and terminating a real stalled worker process.

Focused existing regression from repository root:

```bash
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python -B -m pytest -q tests/test_predict.py tests/test_enrich.py tests/test_rules.py tests/test_interpret.py tests/test_context_scope_block.py tests/test_context_scope_contract.py --basetemp=experiments/batch_v2/checks/output/pytest-tmp -p no:cacheprovider
```

Result: 189 passed. This is focused regression, not a claim that the entire repository regression ran.

```bash
python -B experiments/batch_v2/examples/generic-choice/run_example.py
```

Result: fixture run completed, 8 vectors, 24 rows, 12 synthetic inferences. Recollection and resume were exercised by tests without adding inference calls. Runtime artifacts are generated under results/ and checks/output/ and excluded from publication.

## Astra deviation decisions

D01 — Credentialless clone failed. Astra approved connector-backed exact-SHA retrieval, preserving provenance and lease-protected publication. Snapshot verification resolved this issue. The initial patch transport added trailing newlines; production files were restored from exact connector text and all 76 blob hashes were verified before final checks.

D02 — PR branch lacked the merged PR #19 dependency. Astra approved integrating main into the feature branch using a two-parent commit and main's exact production tree. No production source is edited. This is not a merge of PR #21 into main.

D03 — Browser execution unavailable. Playwright package exists but its Chromium executable does not. Managed Chromium installation under checks/output failed with a truncated ZIP. Cloud browser rejected file:// report navigation under its security policy, explicitly disallowing workarounds. Browser attempts stopped. Astra accepts delivery for review with actual browser acceptance OPEN, not full completion. HTML escaping and emitted filter markup are mechanically tested; that does not substitute for browser interaction.

D04 — First focused regression command used workspace cwd, causing one relative-path example test to fail (188 passed, 1 failed). Astra directed rerun from repository root. Corrected command passed all 189 tests without production changes.

Astra also reviewed worker termination, stale active-call tracking, failed-worker status propagation, run-level shared timing, pre-run distributions, replay support gating, production JSON hashing and streaming model-file SHA256 fingerprints. These fixes are implemented. Replay support is limited to the four mechanically tested adapter/type combinations, recorded with a parity revision and source/adapter hashes.

## Remaining acceptance

1. On the Mac, open a generated report.html: verify 8 overview rows, vector selection, noise and tag filtering, horizontal scrolling on narrow screens and raw evidence links. Or, with Playwright and Chromium installed:

```bash
node experiments/batch_v2/checks/browser-check.cjs <existing-run-folder>
```

This browser script is supplied but did not pass here because the browser could not launch. Actual visual interaction remains unverified.

2. Run the live example in the existing Mac MLX environment. Check local-path SDK loading (including local_files_only support), requested/effective temperature observability and real model responses. No live inference, model download, or claim of live accuracy was made here.

3. Review this PR; merge remains Sharon's separate decision.
