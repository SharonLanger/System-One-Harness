"""Loaded-agent capabilities using reviewed static limits; no file fingerprints."""
from copy import deepcopy
import importlib
import json
from pathlib import Path

from .budget import InspectionUnavailable, make_report
from .budget_adapters import inspect_request

from .model_limits import TYPED, CODE, PROFILES


def unavailable(model, message, request_id=None):
    raise InspectionUnavailable(make_report(model, request_id=request_id), message)


def verify_observation(model, observed):
    profile = next((p for p in PROFILES if p.model_id == model), None)
    if profile is None:
        unavailable(model, 'No supported inspection profile for requested model')
    if profile.status == 'candidate':
        unavailable(model, 'Code-model profile is candidate only; intended runtime qualification is pending')
    if observed.get('model_id') != model:
        binding = observed.get('local_identity')
        if not (isinstance(binding, dict)
                and binding.get('raw_model_id') == observed.get('model_id')
                and binding.get('raw_model_dir') == observed.get('model_dir')
                and isinstance(binding.get('resolved_model_id'), str)
                and binding['resolved_model_id']
                and binding['resolved_model_id'] == binding.get('resolved_model_dir')):
            unavailable(model, 'Unverified loaded metadata: model_id')
    expected = {'max_len': profile.max_len, 'head_max_len': profile.head_max_len,
                'hooks_present': False, 'tokenizer_available': True}
    for field, value in expected.items():
        if field not in observed or observed[field] != value:
            unavailable(model, f'Unverified loaded metadata: {field}')
    return profile


def observe_identity(agent):
    """Filesystem proof from actual loaded fields; never from requested settings."""
    raw_id, raw_dir = str(agent.model_id), str(agent.model_dir)
    binding = None
    try:
        id_path = Path(raw_id).expanduser().resolve(strict=True)
        dir_path = Path(raw_dir).expanduser().resolve(strict=True)
        if id_path.is_dir() and dir_path.is_dir() and id_path == dir_path:
            binding = {'raw_model_id': raw_id, 'raw_model_dir': raw_dir,
                       'resolved_model_id': str(id_path), 'resolved_model_dir': str(dir_path)}
    except (OSError, RuntimeError, ValueError):
        pass
    return {'model_id': raw_id, 'model_dir': raw_dir, 'local_identity': binding}


def _observe_agent(agent, config):
    """Observe the actual loaded MLX agent; no source/config hashes or asset reload."""
    if type(agent).__module__ != 'laya_mlx.agent' or type(agent).__name__ != 'Agent':
        unavailable(config.model, 'Opaque/custom agent requires an explicit inspection provider')
    module = importlib.import_module('laya_mlx.agent')
    common = importlib.import_module('laya_mlx.common')
    hooks = importlib.import_module('laya_mlx.hooks')
    if type(agent) is not module.Agent:
        unavailable(config.model, 'Unsupported agent implementation')
    if any(name in agent.__dict__ for name in _METHODS):
        unavailable(config.model, 'Overridden SDK prediction/encoding methods are unsupported')
    return {**observe_identity(agent), 'revision': getattr(agent, 'revision', None),
            'max_len': agent.cfg.get('max_len'), 'head_max_len': agent.cfg.get('head_max_len'),
            'hooks_present': bool(hooks.compose_hooks(agent.hooks)),
            'tokenizer_available': callable(getattr(agent.tok.backend, 'encode', None))}, common, hooks


class _AgentTokenizer:
    def __init__(self, agent, common, observed):
        self.tok, self.common = agent.tok, common
        self.metadata = {'source': 'loaded_agent_tokenizer', 'runtime': 'laya-mlx'}
        for name in ('cls_token','sep_token','mask_token','cls_token_id','sep_token_id','mask_token_id'):
            setattr(self, name, getattr(self.tok, name))

    def encode(self, text):
        # The same SDK lock protects both inspector and normal prediction encoding.
        return self.common.encode_text(self.tok, text, add_special_tokens=False)['input_ids']


_METHODS = ('predict', 'predict_batch', '_encode_state', '_to_internal', '_check_question')
_SPECIAL_FIELDS = ('cls_token', 'sep_token', 'pad_token', 'mask_token',
                   'cls_token_id', 'sep_token_id', 'pad_token_id', 'mask_token_id')


def _callable_identity(value):
    return id(getattr(value, '__self__', None)), getattr(value, '__func__', value)


class VerifiedInspector:
    def __init__(self, agent, config, profile, observed, common, hooks):
        self.agent, self.config, self.profile, self.hooks = agent, config, profile, hooks
        self._cfg = deepcopy(agent.cfg)
        self._tokenizer = _AgentTokenizer(agent, common, observed)
        self._observed = deepcopy(observed)
        self._methods = {name: _callable_identity(getattr(agent, name, None)) for name in _METHODS}
        with common._TOKENIZE_LOCK:
            self._backend = json.loads(agent.tok.backend.to_str())
            self._special = {name: getattr(agent.tok, name) for name in _SPECIAL_FIELDS}

    def _check_integrity(self, request_id=None):
        model = self.profile.model_id
        if any(name in self.agent.__dict__ or _callable_identity(getattr(self.agent, name, None)) != identity
               for name, identity in self._methods.items()):
            unavailable(model, 'Managed SDK prediction/encoding methods changed', request_id)
        if self.agent.cfg != self._cfg or self.agent.tok is not self._tokenizer.tok or self.hooks.compose_hooks(self.agent.hooks):
            unavailable(model, 'Managed configuration/tokenizer changed or SDK hooks are active', request_id)
        with self._tokenizer.common._TOKENIZE_LOCK:
            tok = self.agent.tok
            if (tok.backend.truncation is not None or tok.backend.padding is not None
                    or json.loads(tok.backend.to_str()) != self._backend
                    or any(getattr(tok, name) != value for name, value in self._special.items())):
                unavailable(model, 'Managed tokenizer semantics changed', request_id)

    def validate_request(self, state, questions):
        """Preserve the compatible SDK's input errors outside inspection failure wrapping."""
        self._check_integrity()
        if state is None:
            raise TypeError('state must not be None; pass a string, dict, or list')
        for name, definition in questions.items():
            self.agent._check_question(name, definition)

    def inspect(self, state, questions, *, request_id=None):
        p = self.profile
        self._check_integrity(request_id)
        report = inspect_request(self._tokenizer, state, questions, model=p.model_id, max_len=p.max_len,
                                 head_max_len=p.head_max_len, request_id=request_id)
        report['model'].update(observed_id=self._observed['model_id'], resolved_revision=self._observed.get('revision'),
                               runtime='laya-mlx', adapter='mlx-sequence-v1', qualification=p.status)
        return report


def verified_provider(agent, config):
    """Default provider. Unknown capabilities fail closed; initialization stays lazy."""
    # Unknown/candidate profiles are refused before importing any SDK modules.
    if config.model != TYPED.model_id:
        verify_observation(config.model, {})
    try:
        observed, common, hooks = _observe_agent(agent, config)
        profile = verify_observation(config.model, observed)
        return VerifiedInspector(agent, config, profile, observed, common, hooks)
    except (InspectionUnavailable, TimeoutError):
        raise
    except (ImportError, AttributeError):
        unavailable(config.model, 'Required loaded checkpoint/runtime inspection metadata is unavailable')
