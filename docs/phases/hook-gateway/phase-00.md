# Phase 0 — baseline (in progress)

Upstream commit: 984aa6754cd6fd76087672d42fb2b5e1ea9ce12b.
Verified Git tree: 3126bc3d8336ba6868b7cea2579e0a3b2d15668f.
291 blobs verified against their exact Git SHA and original modes.
No open PRs observed at start; source-root API still uses cwd.

D01 — repository transport: Authenticated Git clone was unavailable (`could not read Username for https://github.com`). Astra approved materializing a complete immutable upstream tree through the authenticated GitHub connector in a dedicated directory, with exact Git blob/mode/tree verification. Local Git history is bookkeeping only. Published phase commits use real GitHub parent SHAs and lease-protected feature-branch updates. This substitutes transport for clone/worktree/push; it does not waive isolation, ancestry, phased testing, integration, or review requirements.

Setup: npm ci succeeded; npm run build succeeded. An initial test invocation before build failed due to missing dist; this is setup evidence, not baseline product failure. Post-build npm test: 122 passed, 0 failed. Full post-build Python baseline running. Six new invalid-input/unsupported-event characterization cases passed.

Official schema lookup unavailable through browsing. Consumed field requirements remain provisional; no adapter release until verified. Plugin assets and setup preference absent. Root integration waits for the agreed API; no flow/formatter edits made.

No application source changes yet. No real model calls or live Claude activation.

D02 — official schema unavailable: https://code.claude.com/docs/en/hooks lookup returned isError without content. Supported CLI version is unavailable in this workspace. Astra permits isolated upper-layer development against the explicit application contract, but prohibits adapter release/activation/caller migration until verification succeeds.

D03 — root dependency: owner/PR unavailable; reviewed root-based resolution API not available. Astra permits upper-layer injected tests and fake-based adapter work, but prohibits real integration through cwd substitution or duplicated root logic.

Characterization updated: eight cases pass, including accepted literal JSON output and multiple_relevant empty stdout via injected deterministic flow/formatter. This proves the active transport contract, not model selection quality.

Flow reason inventory from file_method_context.py: deadline_exceeded, excluded, extractor_error, ineligible_request, invalid_dependency_budget, invalid_fallback_budget, invalid_reference, model_error, multiple_files, no_file, source_changed, unsupported_request, plus resolver statuses and method_selection reason forwarding. Phase4 must enumerate the forwarded sets before final mapping.

Post-build full Python baseline: 548 passed, 2 failed, 3 skipped in184.00s. Failures:
- tests/test_flow_branches.py::test_explicit_outcomes_never_trigger_fallback[candidate-0.95-0.5-multiple_undecided]
- tests/test_method_selection.py::test_policy_rejections_and_unknown_choice_fail_closed
Both are selection policy baseline cases; assigned to Astra, unchanged. Upper-layer progress permitted by Astra D02/D03 after inventory; adapter/full-flow readiness blocked.

Forwarded selection reasons: no_candidates, candidate_budget_exceeded, ambiguous_candidates, input_budget_exceeded, method_undecided, no_single_match, multiple_undecided, multiple_relevant, unknown_candidate. Resolver statuses forwarded by flow remain explicit unsupported/missing/ambiguous resolution outcomes to enumerate at adapter work.

Phase0 status: baseline inventoried; upper-layer work permitted. Official schema and reviewed root API remain release dependencies.

D04 — stale selection-policy fixtures reconciled: Astra inspected Sharon's commit 5cd63cd027365099be0842316b0807af1c62607f, which removed distance_from_boundary from method selection. High-confidence noul=0.5 correctly means multiple_relevant. Corrected two stale expected values and added true low-answer-confidence multiple_undecided cases at block/flow layers, preserving one-call/no-fallback assertions. Production policy unchanged. Both affected modules: 28 passed in19.54s.
