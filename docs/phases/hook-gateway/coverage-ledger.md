# Coverage ledger — partial implementation, not Phase6 completion

The collected parameter inventory is recorded separately. Existing active-hook regression tests remain in place. Test-only policy corrections follow Astra D04; they do not change model policy.

## Unit scenario assertions

- S01: baseline::test_active_hook_context_and_multiple_relevant[context]; transport::test_literal_output; preparation::test_actual_formatter_root_api. Literal envelopes/text independently asserted. Real full-flow replacement remains Phase5.
- S02: baseline multiple_relevant parameter; transport process-noop parameter; preparation::test_expected_flow_refusals[multiple_relevant]. Exact reason and empty output.
- S03: common::test_missing_common[session_id]/test_invalid_common parameter matrix. Failure field and zero calls.
- S04: transport::test_mismatch_keeps_both_event_names; common::test_mismatched_names_do_not_dispatch. Pair evidence and zero calls.
- S05: common::test_unknown_requires_no_feature_metadata. Unsupported event does not require prompt/root.
- S06: event::test_missing_prompt/test_wrong_prompt_type. Field-specific failure and zero calls.
- S07: event::test_prompt_preserved_and_one_handler empty/whitespace parameters. Valid string preserved and handler called once.
- S08: transport process failure/throw/timeout parameters; preparation::test_operational_flow_failures exhaustive parameters. Errors retain explicit codes.
- S09: transport::test_bad_result/test_malformed_outcome_fields; event::test_bad_handler_result; preparation::test_bad_flow_result_never_formats. No malformed result serialized.
- S10: transport::test_literal_output/test_name_pair_unicode_and_limit/process-context; UTF8 byte count and round-trip characters.
- S11: common::test_metadata_forward_compatibility_and_immutability; event::test_main_to_event_to_handler_and_extra_metadata. Raw fields preserved; logs contain prompt length only.
- S12: common::test_invocations_do_not_share_derived_state; transport::test_concurrent_invocations_have_distinct_correlated_ids. Independent state/IDs for same session.
- S13: preparation::test_invalid_explicit_root/test_missing_or_file_root. Root failure precedes model work.
- S14: preparation::test_root_provenance_and_cwd_preserved. Root/cwd metadata distinct. Actual root-based reference resolution remains BLOCKED.
- S15: preparation::test_disabled_does_not_load_config_or_sdk/test_real_gateway_reports_explicit_unfinished_boundary[False]. No configuration load/SDK/flow/formatter work.
- S16: preparation::test_formatter_exception/test_invalid_formatter_output/test_timeouts_propagate_without_later_work[formatting]. Formatting errors distinct; timeouts propagate.

Prefixes: baseline=tests/test_gateway_migration_baseline.py; transport=tests/test_hook_gateway_transport.py; common=tests/test_hook_common_dispatch.py; event=tests/test_user_prompt_dispatch.py; preparation=tests/test_prompt_context_preparation.py.

## A–F plan coverage and remaining work

A parsing/CLI/input ceiling/deadline: transport bad_arguments/bad_input/name_pair_unicode_and_limit/process tests. Additional CLI budget boundary combinations remain final audit work; do not claim every A parameter completed solely from group mapping.
B common required/optional type matrices: common missing/invalid field tests. Prompt matrices: event tests. Extra metadata and raw immutability explicitly asserted.
C identity seam/override prevention: common tests. Explicit-root validation and provenance: preparation tests. Actual resolution precedence, identical filenames, traversal/symlink access regression C08–C10 remain root-API/Phase5 dependencies; existing source tests were not removed.
D routing/order/call counts/result propagation: common input_order_and_one_dispatch, event outcome/missing/bad-result tests. Active default feature is explicitly blocked, not represented as completed.
E literal protocol, zero bytes, native/Python/logger noise, logger exceptions, broken pipe partial-output accounting, validated session correlation, feature timing, concurrent IDs: transport/event tests. Global file-append locking is deferred under the plan. Replay-caller migration E12 remains Phase5.
F real replacement full flow, source/dependency fidelity, launch-caller migration: NOT COMPLETED. Existing accumulated source/flow regressions run independently; they do not prove the new gateway's complete real integration. Plugin F11 and live Claude F12 remain unavailable/deferred.

Phase6 must expand group mappings into every required individual node and resolve all in-scope pending assertions before merge. This ledger makes remaining work visible; it is not a waiver or a coverage percentage claim.
