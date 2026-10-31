"""Immutable, locally verified inspection profiles. No network lookups."""
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import importlib
import importlib.metadata
import json
from pathlib import Path

from .budget import InspectionUnavailable, make_report
from .budget_adapters import ExactTokenizer, inspect_request

SOURCE_HASHES = (
    ('agent.py','3ceebd3f4acac3ef87718992f0df140c59120e10db7d213365eb1c956a358ee0'),
    ('runtime.py','b36ea0dfddeb8f0a9393b5d77a127ca120505f58009e8e2eb91c3b3a92830883'),
    ('common.py','ca7cac656325bcb5981980e757635642b53eafcdf2010f54c0b79b064e21632b'),
    ('prepared.py','45d87fcdab6359f2f01019cbb70e51a461cb591f268b62df9b443101fb0c358e'),
    ('tokenizer.py','3eb911e1a381f38559f45e09713ea2b1067069024a86d709570a46cd78c0e4a4'),
    ('hooks.py','699c2212cb6aa8aeada9592295aab2a7109751c3bd1b59a6617670c29e09704d'),
)


@dataclass(frozen=True)
class BudgetProfile:
    model_id: str
    revision: str
    max_len: int
    head_max_len: int
    config_sha256: str
    checkpoint_config_sha256: str
    status: str = 'host_qualified_mac_pending'
    tokenizer_sha256: str = '6c8aaa9a542084f2457eab775d4eeb51f92a70c0fd9de28d5edb0ddec3c08d30'
    runtime_version: str = '0.6.0'
    runtime_revision: str = '2159c6c9988e4cbfd6281db1888cef45de09cea9'
    tokenizer_version: str = '0.23.3'
    adapter_version: str = 'mlx-sequence-v1'


TYPED = BudgetProfile('aac6fef/laya-typed-decisions-mlx','f9e501c2080cc57c13d6887820329758f5351125',1024,256,
                      '08d4cf3ac4dca381759441b85b91a6d40e688471dcd33d15d6649eb0a9a854d1',
                      'd99c800b818cb1a60734adba961c27abeaff2d142bb9fc473edb34b7de32fde9')
CODE = BudgetProfile('tindang/laya-code','f3d6bd2344e4750dd917f95d40ceacfa81bb81db',512,192,
                     '50044de60daaa73df97d262e15a40d4faf0160e7d742df64b377877a1320dd12',
                     '41a92ccbc83c2d508413db1ef51640c99aae491c1a1388545b0c3a2c023453e1',status='candidate')


def unavailable(model, message, request_id=None):
    raise InspectionUnavailable(make_report(model, request_id=request_id), message)


def verify_observation(model, observed):
    profile = next((p for p in (TYPED, CODE) if p.model_id == model), None)
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
    expected = {'revision': profile.revision,
                'runtime_version': profile.runtime_version, 'tokenizer_version': profile.tokenizer_version,
                'source_hashes': dict(SOURCE_HASHES), 'tokenizer_sha256': profile.tokenizer_sha256,
                'config_sha256': profile.config_sha256, 'checkpoint_config_sha256': profile.checkpoint_config_sha256,
                'max_len': profile.max_len, 'head_max_len': profile.head_max_len,
                'hooks_present': False, 'backend_matches_files': True}
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


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _observe_agent(agent, config):
    """Read actual loaded identity. Requested configuration is never used as evidence."""
    if type(agent).__module__ != 'laya_mlx.agent' or type(agent).__name__ != 'Agent':
        unavailable(config.model, 'Opaque/custom agent requires an explicit verified inspection provider')
    modules = {name: importlib.import_module('laya_mlx.' + name.removesuffix('.py')) for name, _ in SOURCE_HASHES}
    if type(agent) is not modules['agent.py'].Agent or type(agent.tok) is not modules['tokenizer.py'].Tokenizer:
        unavailable(config.model, 'Unsupported agent/tokenizer implementation')
    if any(name in agent.__dict__ for name in ('predict','predict_batch','_encode_state','_to_internal','_check_question')):
        unavailable(config.model, 'Overridden SDK prediction/encoding methods are unsupported')
    cache = getattr(agent, '_prefix_cache', None)
    if cache is not None and type(cache) is not modules['prepared.py'].PrefixCache:
        unavailable(config.model, 'Unsupported SDK prefix cache')
    source_hashes = {name: _sha(module.__file__) for name, module in modules.items()}
    folder = Path(agent.model_dir)
    vocab, config_path = folder/'tokenizer/tokenizer.json', folder/'tokenizer/tokenizer_config.json'
    expected_tok = ExactTokenizer(vocab, config_path)
    common, hooks = modules['common.py'], modules['hooks.py']
    with common._TOKENIZE_LOCK:
        backend_matches = json.loads(agent.tok.backend.to_str()) == json.loads(expected_tok.backend.to_str())
        backend_matches = backend_matches and all(getattr(agent.tok, key) == getattr(expected_tok, key) for key in
                                                  ('cls_token','sep_token','pad_token','mask_token','cls_token_id','sep_token_id','pad_token_id','mask_token_id'))
    stored_config = json.loads((folder/'rl_agent_config.json').read_text())
    if agent.cfg != stored_config:
        unavailable(config.model, 'Loaded checkpoint configuration differs from verified files')
    return {**observe_identity(agent), 'revision': agent.revision,
            'runtime_version': importlib.metadata.version('laya-mlx'),
            'tokenizer_version': importlib.metadata.version('tokenizers'), 'source_hashes': source_hashes,
            **expected_tok.fingerprints, 'checkpoint_config_sha256': _sha(folder/'rl_agent_config.json'),
            'max_len': agent.cfg.get('max_len'), 'head_max_len': agent.cfg.get('head_max_len'),
            'hooks_present': bool(hooks.compose_hooks(agent.hooks)), 'backend_matches_files': backend_matches}, common, hooks


class _AgentTokenizer:
    def __init__(self, agent, common, observed):
        self.tok, self.common = agent.tok, common
        self.fingerprints = {k: observed[k] for k in ('tokenizer_sha256','config_sha256','tokenizer_version')}
        for name in ('cls_token','sep_token','mask_token','cls_token_id','sep_token_id','mask_token_id'):
            setattr(self, name, getattr(self.tok, name))

    def encode(self, text):
        # The same SDK lock protects both inspector and normal prediction encoding.
        return self.common.encode_text(self.tok, text, add_special_tokens=False)['input_ids']


class VerifiedInspector:
    def __init__(self, agent, config, profile, observed, common, hooks):
        self.agent, self.config, self.profile, self.hooks = agent, config, profile, hooks
        self._cfg = deepcopy(agent.cfg)
        self._tokenizer = _AgentTokenizer(agent, common, observed)
        self._observed = deepcopy(observed)

    def inspect(self, state, questions, *, request_id=None):
        p = self.profile
        if self.agent.cfg != self._cfg or self.agent.tok is not self._tokenizer.tok or self.hooks.compose_hooks(self.agent.hooks):
            unavailable(p.model_id, 'Managed configuration/tokenizer changed or SDK hooks are active', request_id)
        if self.agent.tok.backend.truncation is not None or self.agent.tok.backend.padding is not None:
            unavailable(p.model_id, 'Loaded tokenizer has active truncation/padding', request_id)
        report = inspect_request(self._tokenizer, state, questions, model=p.model_id, max_len=p.max_len,
                                 head_max_len=p.head_max_len, request_id=request_id)
        report['model'].update(observed_id=self._observed['model_id'], resolved_revision=self._observed['revision'], runtime='laya-mlx',
                               runtime_version=self._observed['runtime_version'], runtime_revision=p.runtime_revision,
                               adapter=p.adapter_version, qualification=p.status)
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
    except (ImportError, AttributeError, FileNotFoundError, importlib.metadata.PackageNotFoundError):
        unavailable(config.model, 'Required loaded checkpoint/runtime inspection metadata is unavailable')
