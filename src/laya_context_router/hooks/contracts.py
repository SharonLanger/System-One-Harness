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
    def __init__(self, code, stage, field=None, **evidence):
        super().__init__(f'{stage}: {code}' + (f' ({field})' if field else '') +
                         (f' {evidence!r}' if evidence else ''))
        self.code, self.stage, self.field = code, stage, field
        self.evidence = evidence

def validate_result(result):
    def nonempty(value):return isinstance(value,str) and bool(value.strip())
    if isinstance(result, Context) and isinstance(result.text,str) and result.text and nonempty(result.feature_id):
        return result
    if isinstance(result, Noop) and nonempty(result.reason) and nonempty(result.feature_id):
        return result
    if (isinstance(result, Failure) and nonempty(result.code) and nonempty(result.stage)
            and (result.field is None or nonempty(result.field)) and isinstance(result.message,str)):
        return result
    raise ValidationError('invalid_result', 'result')
