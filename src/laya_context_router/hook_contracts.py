"""Internal outcomes; only the gateway owns Claude protocol serialization."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Context:
    text: str
    feature_id: str = 'prompt_context_enrichment'

@dataclass(frozen=True)
class Noop:
    reason: str
    feature_id: str = 'prompt_context_enrichment'

@dataclass(frozen=True)
class Failure:
    code: str
    stage: str
    field: str | None = None
    message: str = ''

class ValidationError(ValueError):
    def __init__(self, code, stage, field=None):
        super().__init__(f'{stage}: {code}' + (f' ({field})' if field else ''))
        self.code, self.stage, self.field = code, stage, field

def validate_result(result):
    if isinstance(result, Context) and isinstance(result.text, str) and result.text:
        return result
    if isinstance(result, Noop) and isinstance(result.reason, str) and result.reason:
        return result
    if isinstance(result, Failure) and result.code and result.stage:
        return result
    raise ValidationError('invalid_result', 'result')
