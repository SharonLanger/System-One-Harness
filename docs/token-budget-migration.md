# Current PR23 contract

Ordinary `predict()` remains compatible and does not perform budget inspection; the SDK may retain its existing truncation behavior. Use `predict_strict()` for pre-inference inspection and rejection. Supplying an inspection provider alone does not enable strict mode.

`strict=True` is available on the shared QuestionBlock/Block runtime, ticket_triage, ticket_triage_v2, requested_action and context_scope. Method selection (legacy and V2) and all flows remain exactly as main and do not expose strict selection. Existing experiments remain exactly as main; the only new experiment files are the seven manual `experiments/tokenizer_smoke/` scripts/documentation. Requested action retains main's default temperature 1.0 and explicit caller overrides.

Limits are centralized in `laya/model_limits.py` with source URLs, review date and periodic review guidance. New models require explicit entries. Strict mode counts with the loaded tokenizer; source/package/tokenizer-file hash gates and copied tokenizer assets are removed. Managed loaded-object integrity checks remain. CODE is still a refused candidate.

Unit tests use mock tokenizers and establish accounting/control flow only. Actual tokenizer parity and live Mac compatibility remain unverified. Sharon runs the manual local-checkpoint smoke cases; no live model, download or campaign is part of this change. Raw token-budget evidence is excluded from the PR tree.

## Handling a strict refusal

`InputTokenBudgetExceeded` reports measured content loss; `InspectionUnavailable` reports a missing or unsupported inspection capability; `InspectionFailed` reports unexpected inspection failure. All inherit `InputBudgetError` and carry an independent JSON-safe report with a correlation ID. Strict rejection sends no request to inference, though model loading/warmup may already have happened. Strict mode never falls back to ordinary prediction. Success retains the ordinary response contract.

Inspect the reported state, instruction, option or shared-head boundary before choosing a caller policy. No automatic shortening, retry or model switch is added. See `examples/budget_diagnostics.py` for a minimal diagnostic consumer.
