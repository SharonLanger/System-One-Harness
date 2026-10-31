# Building-block refactor verification

Independent review date: 2026-10-31. Scope: practical offline demo, not live model accuracy.

The runtime, typed catalogs, V2 blocks, thin compatibility adapters, and actual test assertions were reviewed against README/design/test-plan. No blocking runtime or selection correctness defect was found. The abbreviated-outline legacy route is an explicit, documented compatibility exception: versioned outlines use V2; invalid explicit schema versions do not fall back.

## Execution evidence

- `python -m pytest tests/block_runtime/test_runtime.py tests/test_v2_blocks.py -q`: 130 passed in 1.08s, independently rerun after the final review fixes and added D07/D12/E06/B05 cases.
- `python -m pytest tests/test_block_legacy_characterization.py tests/test_v2_flow_composition.py tests/block_runtime/test_wheel.py -q`: 40 passed in 9.55s, including real TypeScript outline/extract and isolated wheel execution.
- Final targeted runtime, blocks, flow, wheel and characterization run: 182 passed in 10.18s.
- Complete Python regression suite: 1012 passed, 3 skipped in 203.46s. The final added test-only assertions were also covered by the 182-test targeted run; there were no later production changes.
- Final TypeScript suite: 122 passed, zero skipped (npm --prefix typescript-helper test); helper build passed.
- No live model inference was performed.

Initial meaningful failing runtime evidence was unavailable because pytest was absent at that stage. This report does not claim universal test-first development or reconstruct red evidence from later green results.

## Case map

Names below are exact pytest function names; parametrized variants are included. File aliases: **L** = `tests/test_block_legacy_characterization.py`; **R** = `tests/block_runtime/test_runtime.py`; **V** = `tests/test_v2_blocks.py`; **F** = `tests/test_v2_flow_composition.py`; **W** = `tests/block_runtime/test_wheel.py`; **C** = `tests/test_config.py`; **P** = `tests/test_predict.py`. “Partial” identifies a concrete remaining assertion gap, not an accepted deferral. Documentation cases are review evidence rather than automated tests.

| Cases | Evidence | Assessment |
| --- | --- | --- |
| A01, A02 | L `test_A01_A02_ticket_capture_exact_payload_and_independent_decisions`; V `test_A01_A02_ticket_exact_payload_and_mixed_decision_parity` | Covered |
| A03, A04 | L `test_A03_A04_method_exact_payload_maps_and_accepted_result`; V `test_A03_A05_A08_G09_method_exact_legacy_parity` | Covered |
| A05 | L `test_A05_method_no_selection_reasons`; V `test_A03_A05_A08_G09_method_exact_legacy_parity` | Covered |
| A06 | L `test_A06_skips_do_not_load_or_predict`; V `test_A06_D09_skips_zero_model_calls` | Covered |
| A07 | L `test_A07_duplicate_names_disambiguate_by_location`, `test_A07_invalid_candidates_fail_before_model`; V `test_D02_method_full_outline_contract` | Covered across legacy and V2 input tests |
| A08 | L `test_A08_payload_and_source_mapping_are_independent_copies`; V `test_A03_A05_A08_G09_method_exact_legacy_parity`, `test_D11_sdk_question_mutation_does_not_leak_to_next_run` | Covered |
| A09 | L `test_A09_unicode_character_budget_exact_boundary_and_overflow`; V `test_A09_D15_unicode_exact_character_budget` | Covered |
| A10 | L `test_A10_public_signatures_and_plain_dictionary_contract` | Covered |
| B01 | R `test_supported_types_extract_sdk_answer_without_argmax` | Covered |
| B02 | R `test_shared_and_inline_questions_produce_identical_payloads`, `test_two_question_binding_partial_override_and_independence` | Covered |
| B03 | R `test_two_question_binding_partial_override_and_independence` | Covered |
| B04 | R `test_bad_rule_override_never_predicts`, `test_missing_question_logs_reference_without_preparation`, `test_missing_catalog_directory_has_typed_error` | Covered |
| B05 | R `test_catalog_duplicate_and_json_duplicate_rejected`, `test_block_declaration_loader_rejects_duplicate_local_json_keys` | Covered for rule names/local keys/common strict loader; duplicate question catalog names not separately parameterized |
| B06 | R `test_malformed_catalog_definitions_have_typed_error`, `test_missing_catalog_directory_has_typed_error` | Covered |
| B07 | R `test_block_declaration_requires_one_question_and_rule` | Covered |
| B08 | R `test_bad_rule_override_never_predicts`, `test_missing_default_rule_fails_before_preparation_or_loading` | Covered |
| B09 | R `test_catalog_names_cannot_be_paths` | Covered |
| B10 | R `test_catalog_objects_are_copied_and_cwd_independent` | Covered |
| B11 | R `test_all_shipped_policy_conditions_are_exact`; L `test_A01_A05_default_policy_json_snapshots` | Covered |
| B12 | R `test_supported_types_extract_sdk_answer_without_argmax`; defaults README empty-condition contract | Covered |
| B13 | R `test_catalog_objects_are_copied_and_cwd_independent` | Covered |
| B14 | W `test_new_catalog_and_mocked_block_execute_from_isolated_wheel` | Covered; isolated wheel command passed |
| C01, C02, C03 | R `test_whole_rule_override_and_next_default_are_isolated` | Covered |
| C04, C05 | R `test_two_question_binding_partial_override_and_independence` | Covered |
| C06 | R `test_bad_rule_override_never_predicts` | Covered |
| C07 | R `test_all_wrong_type_rules_fail_at_declaration`, `test_all_wrong_pairings_log_and_stop_before_preparation_or_load` | Covered |
| C08 | R `test_supported_types_extract_sdk_answer_without_argmax` | Covered |
| C09 | R `test_wrong_metric_rejected` | Covered |
| C10 | R `test_invalid_threshold_rejected`, `test_malformed_catalog_definitions_have_typed_error` | Covered |
| C11 | R `test_metrics_boundaries_and_missing_field` | Covered |
| C12, C13 | R `test_whole_rule_override_and_next_default_are_isolated` | Covered |
| C14 | R `test_question_override_shared_and_inline_payloads` | Covered |
| C15 | R `test_bad_question_override_rejected` | Covered |
| C16 | R `test_question_override_shared_and_inline_payloads`, `test_preparer_runs_once_with_copies_and_changed_text`; V `test_D04_D05_D10_custom_preparation_copies_and_mapping_guard` | Covered |
| C17 | R `test_metrics_boundaries_and_missing_field`, `test_two_and_conditions_fail_in_order` | Covered |
| D01 | V `test_D01_ticket_invalid_input_early`; R `test_input_validation_cannot_be_bypassed_by_custom_preparer` | Covered |
| D02 | V `test_D02_method_full_outline_contract`, `test_D02_G10_versioned_malformed_outline_never_downgrades` | Covered; missing name/signature rely on existing outline validator tests |
| D03 | V `test_A03_A05_A08_G09_method_exact_legacy_parity` | Covered |
| D04 | R `test_preparer_runs_once_with_copies_and_changed_text`; V `test_D04_D05_D10_custom_preparation_copies_and_mapping_guard` | Covered |
| D05 | R `test_input_validation_cannot_be_bypassed_by_custom_preparer` | Covered |
| D06 | R `test_prepared_contract_rejects_before_predict`, `test_extra_prepared_question_is_rejected_before_loading` | Covered |
| D07 | V `test_D07_custom_preparer_calls_real_outline_exactly_once` | Covered |
| D08 | R `test_skip_preserves_state_and_utility_error_cause`, `test_unexpected_prepared_validator_failure_is_typed_with_cause` | Covered |
| D09 | R `test_skip_preserves_state_and_utility_error_cause`; V `test_A06_D09_skips_zero_model_calls` | Covered |
| D10 | V `test_D04_D05_D10_custom_preparation_copies_and_mapping_guard` | Covered for corrupted label mapping; missing candidate map not separately parameterized |
| D11 | V `test_D11_sdk_question_mutation_does_not_leak_to_next_run` | Covered |
| D12 | R `test_invalid_reducer_output_raises_typed_failure_and_preserves_cause`; V `test_D12_method_output_validator_rejects_invalid_domain_result` | Covered |
| D13 | V `test_A03_A05_A08_G09_method_exact_legacy_parity`, `test_A06_D09_skips_zero_model_calls`; R `test_invalid_raw_preserves_response_error` | Covered |
| D14 | V `test_D14_ticket_preserves_blank_and_unicode_text`; R `test_supported_types_extract_sdk_answer_without_argmax` | Covered |
| D15 | V `test_D15_invalid_candidate_limits`, `test_A09_D15_unicode_exact_character_budget`, `test_D04_D15_custom_preparation_cannot_bypass_character_budget`; L `test_A06_skips_do_not_load_or_predict` | Covered by V `test_D15_invalid_input_character_limits_fail_before_prediction` and `test_D15_exact_candidate_limit_and_one_beyond` |
| E01 | R `test_supported_types_extract_sdk_answer_without_argmax` | Covered |
| E02 | R `test_two_question_binding_partial_override_and_independence`; V `test_A01_A02_ticket_exact_payload_and_mixed_decision_parity` | Covered |
| E03 | R `test_invalid_raw_preserves_response_error`; P `test_invalid_response`, `test_invalid_choice` | Covered |
| E04, E05 | R `test_enrichment_once_each_and_raw_is_unchanged`, `test_complete_debug_log_events_and_independent_metrics` | Covered; once-count spy is single-question |
| E06 | R `test_complete_debug_log_events_and_independent_metrics`, `test_noul_distance_rule_rejects_without_changing_yes_semantics` | Covered |
| E07 | R `test_supported_types_extract_sdk_answer_without_argmax` | Covered |
| E08 | R `test_noul_boundary` | Covered |
| E09 | R `test_score_rounding_and_clamping` | Covered |
| E10 | R `test_invalid_raw_preserves_response_error`; P `test_invalid_response` | Covered |
| E11 | R `test_enrichment_once_each_and_raw_is_unchanged`, `test_catalog_objects_are_copied_and_cwd_independent` | Covered |
| E12 | R `test_two_question_binding_partial_override_and_independence` | Covered |
| E13 | R `test_load_failure_not_cached_and_prediction_failure_not_retried` | Covered |
| E14 | R `test_complete_debug_log_events_and_independent_metrics`, `test_all_wrong_pairings_log_and_stop_before_preparation_or_load` | Covered for same successful run events and private input absent from mismatch errors |
| F01, F02 | R `test_config_reuse_dispatch_temperature_language_and_invocation` | Covered |
| F03 | R `test_config_reuse_dispatch_temperature_language_and_invocation`; C `test_bad_config` | Covered |
| F04, F05, F06, F07, F08 | R `test_config_reuse_dispatch_temperature_language_and_invocation` | Covered |
| F09 | R `test_load_failure_not_cached_and_prediction_failure_not_retried` | Covered |
| F10 | R `test_two_question_binding_partial_override_and_independence`; C `test_registry_a_b_a_temperature_language_and_kwargs` | Covered additionally by R `test_changed_rule_and_question_reuse_agent_with_current_payload` |
| G01 | F `test_G01_independent_blocks_keep_names_config_and_named_policy` | Covered |
| G02, G03, G04 | F `test_G02_G03_G04_explicit_branch_and_utility_order` | Covered |
| G05, G06 | F `test_G05_G06_real_typescript_v2_select_then_extract`; V `test_G04_G05_G06_real_outline_selection_extraction` | Covered |
| G07 | F `test_G07_migrated_flow_preserves_bounded_fallback`; `tests/test_flow_branches.py::test_explicit_outcomes_never_trigger_fallback` | Covered |
| G08 | F `test_G08_migrated_flow_forwards_project_resolution_timeout_and_budgets` | Covered |
| G09 | V `test_A03_A05_A08_G09_method_exact_legacy_parity`, `test_A01_A02_ticket_exact_payload_and_mixed_decision_parity`, `test_G09_G14_abbreviated_legacy_outline_retains_explicit_old_entrypoint`; L characterization tests | Covered across fixtures; full old/new equality not repeated for each malformed-input assertion |
| G10 | V `test_G10_G14_compatibility_adapter_routes_full_outline_through_v2`, `test_D02_G10_versioned_malformed_outline_never_downgrades`; L `test_A10_public_signatures_and_plain_dictionary_contract` | Covered |
| G11 | F `test_G11_existing_flow_error_boundary_preserves_noop_reason` | Covered |
| G12 | F `test_G12_imports_do_not_load_agents_or_run_flows` | Covered |
| G13 | F `test_G13_existing_offline_experiment_preserves_summary_and_rule_error` | Covered; invalid named policy injected at unchanged experiment boundary because CLI has no rule flag |
| G14 | V `test_G10_G14_compatibility_adapter_routes_full_outline_through_v2`, `test_G09_G14_abbreviated_legacy_outline_retains_explicit_old_entrypoint`, `test_A03_A05_A08_G09_method_exact_legacy_parity` | Covered by explicit entry points; no destructive git revert |
| H01 | `src/laya_context_router/block_runtime/README.md`, defaults README; R fixture block tests | Reviewed actual imports/names and default/override/result explanation |
| H02 | `src/laya_context_router/building_blocks/questions/method_selection_v2/README.md`; F real TypeScript integration | Reviewed utility/model distinction and full source-outline requirement |
| H03 | block_runtime README wrong-type example; R `test_all_wrong_pairings_log_and_stop_before_preparation_or_load` | Reviewed actual rule types and zero-load behavior |
| H04 | W `test_new_catalog_and_mocked_block_execute_from_isolated_wheel`; `tests/test_packaged_blocks.py::test_both_block_resources_load_from_isolated_wheel` | Covered for new wheel and original wheel regression in the complete Python suite |
| H05 | Complete Python and TypeScript commands above | Passed |
| H06 | This case map and independent review | Covered; review findings resolved and limitations retained |

## Remaining acceptance limits

The four narrow assertion gaps found in review were subsequently closed with dedicated tests (B08, D06, D15, F10). The map covers the required demo cases through direct assertions, existing regressions and documented manual review where appropriate. This is evidence for the declared demo scope, not exhaustive production assurance. Universal test-first red evidence was not obtained: pytest was unavailable for the initial runtime test; this limitation is retained above.

No live accuracy, parallel/thread safety, model downloads, or hook activation is claimed. The legacy implementation and resources remain available for rollback.
