# Current PR23 contract

Ordinary `predict()` remains compatible and does not perform budget inspection; the SDK may retain its existing truncation behavior. Use `predict_strict()` for pre-inference inspection and rejection. Supplying an inspection provider alone does not enable strict mode.

`strict=True` is available on the shared QuestionBlock/Block runtime, ticket_triage, ticket_triage_v2, requested_action and context_scope. Method selection (legacy and V2) and all flows remain exactly as main and do not expose strict selection. Existing experiments remain exactly as main; the only new experiment files are the seven manual `experiments/tokenizer_smoke/` scripts/documentation. Requested action retains main's default temperature 1.0 and explicit caller overrides.

Limits are centralized in `laya/model_limits.py` with source URLs, review date and periodic review guidance. New models require explicit entries. Strict mode counts with the loaded tokenizer; source/package/tokenizer-file hash gates and copied tokenizer assets are removed. Managed loaded-object integrity checks remain. CODE is still a refused candidate.

Unit tests use mock tokenizers and establish accounting/control flow only. Actual tokenizer parity and live Mac compatibility remain unverified. Sharon runs the manual local-checkpoint smoke cases; no live model, download or campaign is part of this change. Raw token-budget evidence is excluded from the PR tree.

## Conflict resolution

Integrated current main `6260d6d0ba948e7506461fa2a06c1fb67dc4268d` while preserving its experiment, flow, method-selection and retired-test decisions. Historical full-suite counts describe earlier snapshots, not this final tree. Final verification is intentionally focused; results are recorded after completion.

## Final focused verification

355 tests passed in 29.82s on the resolved source (exit 0):

```bash
PYTHONPATH=src:. python -m pytest -q tests/test_token_budget_*.py tests/test_requested_action_contract.py tests/test_requested_action_block.py tests/test_v2_blocks.py tests/test_block_legacy_characterization.py tests/test_predict.py tests/test_live_check.py tests/test_method_ambiguity_fallback.py tests/test_prompt_file_list.py tests/test_prompt_hook.py tests/test_v2_flow_composition.py
```

`npm --prefix typescript-helper run build` passed. The first focused run found two missing generated-helper failures and one obsolete exact ticket signature expectation (269 passed, 3 failed). Astra approved build-only recovery and the authorized additive ticket signature correction; all three then passed before the final focused run. Method-selection assertions remained unchanged.

Smoke `run.py --help`, syntax checks for all six Python entry files, and five mocked payload/boundary checks passed without importing tokenizers, laya_mlx, mlx or numpy. Existing experiments, all flows and both method-selection families match pinned main by blob and file mode. No full-suite rerun or live experiment was performed. Raw logs remain outside the repository.
