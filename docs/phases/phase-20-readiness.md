# Phase20 readiness preparation

Objective: provide a runnable, explicit Mac probe and evidence handoff. This is
preparation for Phase20; it does not complete real-model verification.
Starting code:0d1cfceb2f6bbf0f38b4379cdaf76bd10a74f765; Linux x86_64.

Independent preimplementation test planning requested positive/negative/boundary
checks for a one-checkpoint explicit CLI, raw named choice/noul/score validation,
actual-agent metadata rather than requested-value echoes, accepting/rejecting
rules and extraction, configuration reuse, fresh registry, real source helper,
optional confirmed second checkpoint/settings, and honest pending live status.

Tests were written before the module: collection failed with missing
`laya_context_router.live_check`. New tests inject the loader, never real Laya.
They check strict raw answers and processing, malformed raw retention, distinct
configuration reuse, metadata separation, rejected-selection no-op, source error
failure, CLI environment/opt-in gates and output creation/no-overwrite. The
synthetic SDK test returns fixed answers; these are not captured real results.
Existing expectations/fixtures are unchanged.

Implementation: new live_check module,12 readiness tests, README and Mac guide.
Default uses one checkpoint; optional confirmed model/temperatures cover both
checkpoints at defaults and each temperature. Adapter validation remains the
raw-schema authority. Additional independent arithmetic checks compare actual
raw probability gap/entropy, noul distance, score round/clamp extraction and
accept/reject decisions. Source acceptance verifies exact synthetic code; valid
selection rejection/no-match is allowed, technical flow failures are not.
Public metadata is read from the loaded underlying agent, with missing fields
and identity/settings limitations recorded. No assertion equates requested names
to verified checkpoint identity. A fresh registry is not a fresh OS process.

Full-suite commands:

```bash
npm --prefix typescript-helper run build
npm --prefix typescript-helper test
python -m pytest -q
git diff --check
```

Baseline: fresh build/typecheck, Node53/53 and Python415/415 in109.33s.
An intermediate run passed Node53/53 and Python425/425 in116.32s; final review
fixes were made afterward, so this does not count as final-candidate evidence.
Final implementer gate: fresh build/typecheck, Node53/53 and Python427/427
in119.54s, zero failures/skips/xfail. Independent final rerun: fresh build/typecheck, Node53/53 and Python427/427
in111.39s, zero failures/skips/xfail; diffcheck clean.
Focused readiness suite:12 passed; no failures/skips/xfail.
Independent final verification: complete for readiness scope. Reviewer inspected
implementation/tests/docs and independently reran every accumulated suite.
Separate design review found
and resolved two blockers before the final gate: processing checks now use
explicit exceptions instead of optimization-sensitive assertions; the platform
rejection test deterministically simulates Linux and rejects real-loader access
on every host, including Macs. Malformed non-JSON responses retain labelled
bounded diagnostic representations; strict JSON responses retain raw values.
Evidence is fully encoded before exclusive output creation.
Execution mode: mocked SDK only; no real SDK import, load or inference.
Real Laya compatibility: BLOCKED pending supported Mac execution and evidence.
Requested live matrix: NOT RUN; second compatible checkpoint and supported
explicit temperatures are not invented. Actual observed identity/settings,
SDK/model versions and genuine raw JSON remain unknown.
Actual Claude delivery: NOT RUN; no hook/settings activation.
Verifier verdict: VERIFIED for readiness preparation only; BLOCKED for Phase20.
Decision: readiness preparation COMPLETE; Phase20 real verification BLOCKED.
