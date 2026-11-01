# Manual tokenizer smoke checks

Run these yourself on your MLX Mac, from the repository root, using the Python environment with the project and laya-mlx installed. PR #23's predict_strict/block strict support is required.

```bash
python experiments/tokenizer_smoke/valid.py --model-path /absolute/path/to/typed-decisions-checkpoint
python experiments/tokenizer_smoke/oversized_state.py --model-path /absolute/path/to/typed-decisions-checkpoint
python experiments/tokenizer_smoke/oversized_question.py --model-path /absolute/path/to/typed-decisions-checkpoint
python experiments/tokenizer_smoke/oversized_option.py --model-path /absolute/path/to/typed-decisions-checkpoint
python experiments/tokenizer_smoke/oversized_shared_head.py --model-path /absolute/path/to/typed-decisions-checkpoint
```

Or run all five with one model load:

```bash
python experiments/tokenizer_smoke/run.py --case all --model-path /absolute/path/to/typed-decisions-checkpoint
```

Uses the real ticket_triage_v2 building block (not Batch V2), its two questions, the real loaded tokenizer and strict inspection. The valid case should perform one prediction. Oversized cases should raise InputTokenBudgetExceeded before prediction; the script catches that expected rejection and prints PASS. Missing tokenizer support, SDK compatibility problems, unexpected errors, or missing expected violations print FAIL and return exit code 1. The code-model candidate is not supported by this probe.

| Script | Expected measured boundary |
| --- | --- |
| valid.py | Success, one prediction |
| oversized_state.py | state and full_request (total budget) |
| oversized_question.py | instructions |
| oversized_option.py | option_text (per-option cap) |
| oversized_shared_head.py | shared_head_option (options competing for head space) |

The full-request budget and state allowance overlap, so a large state can trigger both. Other additional violations are displayed too. Repetition sizes deliberately exceed the limits by a wide margin; no character-to-token estimates are used for the actual check. These probes test acceptance/rejection and dispatch, not answer accuracy.

No model downloads are requested. A complete local checkpoint and compatible MLX installation are required; the SDK may initialize/warm up when loading. Normal application debug logging still applies. This directory creates no batch campaign, evidence bundle, or saved results. Real execution has been left to Sharon; author validation uses mocks and syntax/help checks only.
