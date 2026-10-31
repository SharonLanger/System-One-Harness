"""Reviewed model limits, not tokenizer/runtime identity verification.

Reviewed: 2026-10-31. Review at least quarterly and after SDK/model changes.
Add a model entry and review its loaded-tokenizer assembly before strict support;
never infer limits from a name or increase them to accept a rejected request.
The MLX adapter follows the cited common.py assembly. Package/source hashes are
not checked. Runtime compatibility and real-tokenizer parity remain unverified
by the mock-only unit suite; callers must use a compatible loaded MLX agent.

Sources (reviewed configuration/source snapshots):
- https://huggingface.co/aac6fef/laya-typed-decisions-mlx/blob/f9e501c2080cc57c13d6887820329758f5351125/rl_agent_config.json
- https://huggingface.co/tindang/laya-code/blob/f3d6bd2344e4750dd917f95d40ceacfa81bb81db/rl_agent_config.json
- https://github.com/mizorewww/laya-mlx/blob/2159c6c9988e4cbfd6281db1888cef45de09cea9/laya_mlx/common.py
"""
from dataclasses import dataclass

OPTION_TEXT_LIMIT = 48  # rendered option text; excludes its marker

@dataclass(frozen=True)
class ModelLimits:
    model_id: str
    max_len: int
    head_max_len: int
    status: str = 'reviewed_limits_live_unverified'

TYPED = ModelLimits('aac6fef/laya-typed-decisions-mlx', 1024, 256)
CODE = ModelLimits('tindang/laya-code', 512, 192, status='candidate')
PROFILES = (TYPED, CODE)
