"""Small lazy SDK boundary; live compatibility awaits Phase 20."""
from copy import deepcopy
import json
import math
from ..log_utils import log

DEFAULT_MODEL = 'aac6fef/laya-typed-decisions-mlx'

class ResponseError(ValueError):
    """The SDK returned unusable prediction data."""


def real_loader(model, **kwargs):
    import laya_mlx
    return laya_mlx.load(model, **kwargs)


def validate_questions(questions):
    from ..questions.models import Question
    if not isinstance(questions, dict) or not questions:
        raise ValueError('questions must be a nonempty named mapping')
    for name, question in questions.items():
        if not isinstance(name, str) or not name or not isinstance(question, dict):
            raise ValueError('invalid question name or definition')
        Question.from_dict({**question, 'name': name})


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _probabilities(probs, keys, name):
    if not isinstance(probs, dict) or set(probs) != set(keys):
        raise ResponseError(f'invalid probability keys: {name}')
    if not all(_finite(v) and 0 <= v <= 1 for v in probs.values()):
        raise ResponseError(f'invalid probability: {name}')
    if not math.isclose(sum(probs.values()), 1, abs_tol=0.001):
        raise ResponseError(f'probabilities must sum to one: {name}')


def validate_response(raw, questions):
    if not isinstance(raw, dict) or not isinstance(raw.get('answers'), dict):
        raise ResponseError('response must contain an answers mapping')
    try:
        json.dumps(raw, allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise ResponseError('response must be strict JSON') from exc
    for name, question in questions.items():
        answer = raw['answers'].get(name)
        if not isinstance(answer, dict) or answer.get('type') != question['type']:
            raise ResponseError(f'invalid answer type: {name}')
        for field in ('confidence', 'answer_confidence'):
            if field in answer and not (_finite(answer[field]) and 0 <= answer[field] <= 1):
                raise ResponseError(f'invalid {field}: {name}')
        if 'action' in answer:
            action = answer['action']
            if not isinstance(action, dict):
                raise ResponseError(f'invalid action: {name}')
            if 'act_probability' in action and not (_finite(action['act_probability']) and 0 <= action['act_probability'] <= 1):
                raise ResponseError(f'invalid action probability: {name}')
        kind = answer['type']
        if kind == 'choice':
            criteria = question['criteria']
            if not isinstance(answer.get('choice'), str) or answer['choice'] not in criteria:
                raise ResponseError(f'invalid choice: {name}')
            _probabilities(answer.get('probabilities'), criteria, name)
        elif kind == 'noul':
            value = answer.get('noul')
            if not (_finite(value) and 0 <= value <= 1):
                raise ResponseError(f'invalid noul: {name}')
        elif kind == 'score':
            if not _finite(answer.get('score')):
                raise ResponseError(f'invalid score: {name}')
            legend = {str(i): label for i, label in enumerate(question['criteria'])}
            if answer.get('legend') != legend:
                raise ResponseError(f'invalid score legend: {name}')
            _probabilities(answer.get('probabilities'), legend, name)
        else:
            raise ResponseError(f'unsupported prediction type: {name}')
    return raw


def predict(text, questions, *, model=DEFAULT_MODEL, loader=None, real=False, config=None, registry=None, inspection_provider=None):
    """Return copied raw JSON, reusing agents only in the provided registry."""
    from .config import RunConfig
    from .registry import AgentRegistry
    validate_questions(questions)
    if config is None:
        config = RunConfig(model=model)
    if registry is None:
        registry = AgentRegistry(loader=loader, real=real, inspection_provider=inspection_provider)
    elif loader is not None or real or inspection_provider is not None:
        raise ValueError('registry owns loader, mode and inspection provider')
    log("DEBUG", "laya", "prediction_started", text=text, questions=questions,
        model=config.model, temperature=config.temperature, lang=config.lang)
    try:
        raw = registry.get_agent(config).predict(text, deepcopy(questions), **config.predict_kwargs())
        log("DEBUG", "laya", "response_received", response=raw)
        result = deepcopy(validate_response(raw, questions))
    except Exception as exc:
        log("ERROR", "laya", "prediction_failed", error=exc)
        raise
    log("INFO", "laya", "response_validated")
    return result

