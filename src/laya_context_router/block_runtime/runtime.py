"""Composition-based execution with one prediction and one enrichment per answer."""
from copy import deepcopy
from pathlib import Path
from .catalog import Catalog
from .contracts import (BlockConfigurationError, BlockInputError, BlockExecutionError,
                        PreparedInput, BlockResult, SkipBlock)
from ..json_utils import load_json
from ..questions.models import Question
from ..laya.predict import predict, predict_strict, validate_response
from ..answers.enrich import enrich_prediction
from ..answers.interpret import extract_answer
from ..answers.rules import accepts
from ..log_utils import log


def _validated(validator, value):
    result = validator(value)
    return value if result is None else result

class Block:
    def __init__(self, declaration, *, validate_input, prepare_input, reduce,
                 validate_output, validate_prepared=None, catalog=None):
        self.catalog = catalog if catalog is not None else Catalog()
        try:
            self.declaration = deepcopy(declaration) if isinstance(declaration, dict) else load_json(Path(declaration))
            if not isinstance(self.declaration, dict): raise ValueError('block must be an object')
            self.name = self.declaration['name']
            if not isinstance(self.name, str) or not self.name: raise ValueError('block name required')
            definitions = self.declaration['questions']
            if not isinstance(definitions, dict) or not definitions: raise ValueError('block questions must be nonempty')
            for name, spec in definitions.items():
                if not isinstance(name, str) or not name or not isinstance(spec, dict): raise ValueError('invalid local question')
                if ('question_ref' in spec) == ('definition' in spec): raise ValueError('exactly one of question_ref/definition required')
                if 'rule_ref' not in spec: raise ValueError('rule_ref required')
            self._resolve({}, {})
        except (ValueError, KeyError, TypeError, OSError) as exc:
            self._error('configuration', 'invalid_declaration')
            if isinstance(exc, BlockConfigurationError): raise
            raise BlockConfigurationError(str(exc)) from exc
        self.validate_input, self.prepare_input = validate_input, prepare_input
        self.reduce, self.validate_output = reduce, validate_output
        self.validate_prepared = validate_prepared

    def _error(self, stage, code, **fields):
        log('ERROR', 'block_runtime', 'failed', block=getattr(self, 'name', '<unknown>'),
            stage=stage, code=code, **fields)

    def _question(self, name, spec):
        if isinstance(spec, str): body = self._shared_question(name, spec)
        elif isinstance(spec, dict) and set(spec) == {'question_ref'}: body = self._shared_question(name, spec['question_ref'])
        elif isinstance(spec, dict): body = spec
        else: raise BlockConfigurationError('question override must be a body or reference')
        return Question.from_dict({**deepcopy(body), 'name': name}).to_predict_dict()

    def _shared_question(self, name, reference):
        try:
            return self.catalog.question(reference)
        except BlockConfigurationError:
            self._error('configuration', 'question_not_found', question=name, question_ref=reference)
            raise

    def _resolve(self, rule_overrides, question_overrides):
        definitions = self.declaration['questions']
        for overrides in (rule_overrides, question_overrides):
            if not isinstance(overrides, dict) or not set(overrides) <= set(definitions):
                raise BlockConfigurationError('unknown override question key')
        questions, rules = {}, {}
        for name, spec in definitions.items():
            original = self._question(name, spec['question_ref'] if 'question_ref' in spec else spec['definition'])
            questions[name] = self._question(name, question_overrides[name]) if name in question_overrides else original
            if original['type'] != questions[name]['type']:
                raise BlockConfigurationError(f'question override changes declared type: {name}')
            rule_name = rule_overrides.get(name, spec['rule_ref'])
            try: rule = self.catalog.rule(rule_name)
            except BlockConfigurationError:
                self._error('configuration', 'rule_not_found', question=name, rule=rule_name)
                raise
            self._compatible(name, questions[name]['type'], rule)
            rules[name] = rule
        return questions, rules

    def _compatible(self, name, kind, rule):
        if kind != rule.question_type:
            self._error('configuration', 'rule_type_mismatch', question=name, rule=rule.name,
                        expected_type=kind, actual_type=rule.question_type)
            raise BlockConfigurationError(f'rule_type_mismatch: {name}: {rule.name} requires {rule.question_type}, question is {kind}')

    def run(self, input_data, *, config, registry, rule_overrides=None, question_overrides=None, prepare_input=None, strict=False):
        try:
            questions, rules = self._resolve({} if rule_overrides is None else rule_overrides,
                                              {} if question_overrides is None else question_overrides)
        except (ValueError, TypeError, KeyError) as exc:
            if isinstance(exc, BlockConfigurationError): raise
            raise BlockConfigurationError(str(exc)) from exc
        try: validated = _validated(self.validate_input, deepcopy(input_data))
        except TimeoutError: raise
        except (ValueError, TypeError, KeyError) as exc:
            self._error('input', 'invalid_input')
            raise BlockInputError(str(exc)) from exc
        log('DEBUG', 'block_runtime', 'configured', block=self.name,
            rules={name: {'name': r.name, 'conditions': r.conditions} for name,r in rules.items()}, config=config)
        try:
            prepared = (prepare_input or self.prepare_input)(deepcopy(validated), deepcopy(questions))
        except SkipBlock as skip:
            return self._skip(skip)
        except TimeoutError: raise
        except Exception as exc:
            self._error('preparation', 'preparation_failed')
            raise BlockExecutionError(f'block {self.name}: preparation failed') from exc
        try:
            if not isinstance(prepared, PreparedInput): raise ValueError('preparer must return PreparedInput')
            if not isinstance(prepared.text, str) or not isinstance(prepared.state, dict): raise ValueError('prepared text/state invalid')
            if not isinstance(prepared.questions, dict) or set(prepared.questions) != set(questions): raise ValueError('prepared question names must match declaration')
            normalized = {}
            for name, body in prepared.questions.items():
                normalized[name] = self._question(name, body)
                if normalized[name]['type'] != questions[name]['type']: raise ValueError('prepared question type changed')
                self._compatible(name, normalized[name]['type'], rules[name])
            prepared = PreparedInput(prepared.text, normalized, deepcopy(prepared.state))
            if self.validate_prepared: self.validate_prepared(prepared, deepcopy(validated))
        except TimeoutError: raise
        except SkipBlock as skip:
            return self._skip(skip)
        except (ValueError, TypeError, KeyError) as exc:
            self._error('preparation', 'invalid_prepared_input')
            raise BlockInputError(str(exc)) from exc
        except Exception as exc:
            self._error('preparation', 'preparation_failed')
            raise BlockExecutionError(f'block {self.name}: preparation validation failed') from exc
        log('DEBUG', 'block_runtime', 'prepared', block=self.name, questions=prepared.questions)
        # predict validates and copies SDK output. Deliberately preserve ResponseError,
        # loader errors and TimeoutError for the flow's existing error boundary.
        if type(strict) is not bool: raise ValueError("strict must be boolean")
        raw = (predict_strict if strict else predict)(prepared.text, deepcopy(prepared.questions), config=config, registry=registry)
        validate_response(raw, prepared.questions)
        decisions = {}
        for name in prepared.questions:
            enriched = enrich_prediction(raw['answers'][name])
            log('DEBUG', 'enrichment', 'completed', block=self.name, question=name, enriched=enriched)
            decided, reason = accepts(enriched, rules[name])
            decisions[name] = {'answer': extract_answer(enriched) if decided else 'undecided',
                               'decided': decided, 'reason': reason}
        data = self._reduce(decisions, prepared.state)
        log('INFO', 'block_runtime', 'completed', block=self.name, decisions=decisions)
        return BlockResult('completed', None, decisions, data)

    def _reduce(self, decisions, state):
        try:
            data = self.reduce(deepcopy(decisions), deepcopy(state))
            return _validated(self.validate_output, data)
        except TimeoutError: raise
        except Exception as exc:
            self._error('reduction', 'invalid_output')
            raise BlockExecutionError(f'block {self.name}: invalid output') from exc

    def _skip(self, skip):
        state = deepcopy(skip.state)
        if not isinstance(state, dict): raise BlockInputError('skip state must be a mapping')
        state.setdefault('reason', skip.reason)
        data = self._reduce({}, state)
        log('INFO', 'block_runtime', 'completed', block=self.name, status='skipped', reason=skip.reason)
        return BlockResult('skipped', skip.reason, {}, data)
