# Phase 4 — PARTIAL, integration blocked

Astra approved only independent preparation/mapping work. The existing active hook, caller launch configurations and real flow are unchanged.

Implemented private explicit-root/config preparation; model-disabled check before config loading; actual collector schema validation; explicit flow-reason classification; actual formatter(project_root) adaptation with distinct formatting failures. The unfinished public handler reports root_api_unavailable after successful preparation. It never calls the flow, formatter or SDK. This is an explicit incomplete boundary, not an enrichment feature completion claim.

Expected Noop reasons: ineligible_request, unsupported_request, no_file, multiple_files, excluded, missing, ambiguous, no_candidates, candidate_budget_exceeded, ambiguous_candidates, input_budget_exceeded, method_undecided, no_single_match, multiple_undecided, multiple_relevant.

Failure reasons: deadline_exceeded, extractor_error, invalid_dependency_budget, invalid_fallback_budget, invalid_reference, model_error, source_changed, unknown_candidate, inaccessible, outside_repository, not_file. Unknown shapes/reasons and inconsistent context/reason combinations fail invalid_flow_result. Every listed reason has a literal independently listed parametrized test. Reusing collector schema validation is contract checking, not independent source-fidelity verification.

D06 — Astra approved explicit unfinished handler and result mapping. Raised TimeoutError propagates through root/config/schema/formatter work to the gateway; explicit flow reason deadline_exceeded maps to Failure. Injected timeout tests cover all four locations and dependent-call suppression; process test checks outer deadline_exceeded/empty stdout/exit0. Ordinary errors remain distinct.

Tests: accumulated focused suite180passed before additional concurrency case. Default gateway model-disabled/rootblocked tests independently assert no real flow/formatter/SDK calls and session-correlated final error records. New concurrency case records distinct invocation IDs for same-session processes (results in final progress record).

Remaining gates: verified supported CLI schema; reviewed root-based reference-resolution API. No owner/PR is known. Current flow still requires cwd and resolves relative references through it. No guessing of its future signature, root-as-cwd substitution, or containment changes performed. Phases5–7 not completed; keep PR draft and do not merge.

Final focused check: `python3 -m pytest -q tests/test_hook_gateway_transport.py tests/test_hook_common_dispatch.py tests/test_user_prompt_dispatch.py tests/test_prompt_context_preparation.py tests/test_gateway_migration_baseline.py`: 181passed in1.37s. Includes same-session concurrent invocation correlation. Unit inventory181collected. Main rechecked at984aa6754cd6fd76087672d42fb2b5e1ea9ce12b; no main advance to integrate. No textual conflicts encountered. Full regression results, once completed, are recorded separately from this final focused candidate.

## Integration completed after ownership clarification

D07 — root ownership clarification and explicit integration mode: merged984aa supplied formatter/navigation root semantics, not a replacement prompt-flow API. Astra withdrew the inferred waiting dependency. This branch adds boolean resolve_from_project_root=False to the existing flow/resolver facade. Legacy defaults retain their ambiguity/search behavior. Gateway opts in with True, raw event cwd remains metadata, and configured repository_root selects the underlying generic helper search base. No resolver algorithm or navigation operation was added. Current source containment remains enforced.

D02 RESOLVED for structural application contract: official Anthropic SDK source pinned at https://github.com/anthropics/claude-agent-sdk-python/blob/1ea8cb74ddcdadbfaa9b20dfa8268e18047851e7/src/claude_agent_sdk/types.py defines BaseHookInput, UserPromptSubmitHookInput, UserPromptSubmitHookSpecificOutput and SyncHookJSONOutput. transcript_path is now a required nonempty string; permission_mode remains optional. No transcript reading/path-existence/absolute-path requirement. Installed CLI version, plugin registration and live delivery remain separate unverified checks.

Integrated Phase4 tests:197passed in8.01s. Legacy resolver/flow regressions:52passed in32.18s. Root-mode tests use actual resolver/helper/formatter with only SDK model mocked. Colliding root/nested names select root in root mode; legacy mode remains ambiguous across both exact candidates. Root/nested/unrelated event cwd and unrelated process cwd preserve output. Traversal, symlink escapes, prefix collisions, missing/ambiguous/absolute references and invalid mode types covered. Temporary root_api_unavailable behavior removed.
