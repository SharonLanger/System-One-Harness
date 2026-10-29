"""Small lazy SDK boundary; live compatibility awaits Phase 20."""
from copy import deepcopy
import json
import math

DEFAULT_MODEL = 'aac6fef/laya-typed-decisions-mlx'

class ResponseError(ValueError):
    """The SDK returned unusable prediction data."""


def real_loader(model, **kwargs):
    import laya_mlx
    return laya_mlx.load(model, **kwargs)


def validate_questions(questions):
    if not isinstance(questions, dict) or not questions:
        raise ValueError('questions must be a nonempty named mapping')
    for name, question in questions.items():
        if not isinstance(name, str) or not name or not isinstance(question, dict):
            raise ValueError('invalid question name or definition')
        if question.get('type') not in ('choice', 'noul', 'score'):
            raise ValueError('unsupported question type')
        if not isinstance(question.get('instructions'), str):
            raise ValueError('question instructions must be a string')


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
        if answer['type'] == 'choice':
            criteria = question.get('criteria', {})
            probs = answer.get('probabilities')
            if answer.get('choice') not in criteria or not isinstance(probs, dict) or set(probs) != set(criteria):
                raise ResponseError(f'invalid choice/probabilities: {name}')
            if not all(isinstance(v, (int,float)) and not isinstance(v,bool) and math.isfinite(v) and 0 <= v <= 1 for v in probs.values()):
                raise ResponseError(f'invalid probability: {name}')
            if not math.isclose(sum(probs.values()), 1, abs_tol=0.001):
                raise ResponseError(f'probabilities must sum to one: {name}')
    return raw


def predict(text, questions, *, model=DEFAULT_MODEL, loader=None, real=False, config=None, registry=None):
    """Return copied raw JSON, reusing agents only in the provided registry."""
    from .config import RunConfig
    from .registry import AgentRegistry
    validate_questions(questions)
    if config is None:
        config = RunConfig(model=model)
    if registry is None:
        registry = AgentRegistry(loader=loader, real=real)
    elif loader is not None or real:
        raise ValueError('registry owns loader and mode')
    raw = registry.get_agent(config).predict(text, deepcopy(questions), **config.predict_kwargs())
    return deepcopy(validate_response(raw, questions))
