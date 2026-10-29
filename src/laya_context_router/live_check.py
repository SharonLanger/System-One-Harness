"""Explicit Mac real-call readiness probe; never imported by normal flows."""
import argparse
from contextlib import redirect_stdout
from copy import deepcopy
import importlib.metadata
import json
import math
import platform
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from .answers.enrich import enrich_response
from .answers.interpret import interpret
from .answers.rules import RulesConfig
from .flows.file_method_context import run as run_flow
from .laya.config import RunConfig
from .laya.predict import predict, real_loader
from .laya.registry import AgentRegistry

QUESTIONS = {
    'fruit': {'type': 'choice', 'instructions': 'Which fruit is mentioned?',
              'criteria': {'apple': 'apple', 'pear': 'pear'}},
    'mentioned': {'type': 'noul', 'instructions': 'Is a fruit mentioned?'},
    'size': {'type': 'score', 'instructions': 'How large is the apple?',
             'criteria': ['small', 'large']},
}
TEXT = 'A large apple is on the table.'
SOURCE = 'export function double(value: number) { return value * 2; }'


def observe(agent):
    """Read only bounded, public scalar metadata. Never attach requested settings."""
    attributes = {}
    unavailable = []
    for name in ('model_id', 'model_name', 'model_dir', 'revision', 'temperature', 'lang_temperatures'):
        try:
            value = getattr(agent, name)
            if isinstance(value, Path):
                value = str(value)
            encoded = json.dumps(value, allow_nan=False)
            if len(encoded) > 4096:
                raise ValueError('metadata exceeds limit')
            attributes[name] = json.loads(encoded)
        except Exception:
            unavailable.append(name)
    return {'class': f'{type(agent).__module__}.{type(agent).__qualname__}',
            'attributes': attributes, 'unavailable': unavailable,
            'limitation': 'Reported attributes may not establish resolved checkpoint identity or effective settings.'}


def check_processing(raw, enriched, decisions, rejected):
    """Independent arithmetic/extraction checks from actual returned data, no labels."""
    def require(condition):
        if not condition:
            raise ValueError('processing result differs from independently computed raw outcome')
    for name, answer in raw['answers'].items():
        if name not in QUESTIONS:
            continue
        kind = answer['type']
        if kind == 'noul':
            expected = 'yes' if answer['noul'] >= 0.5 else 'no'
            require(enriched['answers'][name]['distance_from_boundary'] == round(abs(answer['noul'] - 0.5), 4))
        else:
            values = sorted(answer['probabilities'].values(), reverse=True)
            require(enriched['answers'][name]['probability_gap'] == round(values[0] - values[1], 4))
            entropy = -sum(p * math.log(p) for p in values if p)
            require(enriched['answers'][name]['normalized_entropy'] == round(entropy / math.log(len(values)), 4))
            expected = answer['choice'] if kind == 'choice' else answer['legend'][str(max(0, min(round(answer['score']), len(answer['legend']) - 1)))]
        require(decisions[name] == {'answer': expected, 'decided': True, 'reason': None})
        require(rejected[name] == {'answer': 'undecided', 'decided': False, 'reason': 'field_missing:readiness_missing_field'})


def run_check(*, loader, model=RunConfig().model, second_model=None, temperatures=()):
    """Run with an explicit boundary. CLI supplies the real loader only after opt-in."""
    temperatures = list(temperatures)
    if second_model == model:
        raise ValueError('second checkpoint must differ; aliases still require manual identity verification')
    if temperatures and (len(temperatures) != 2 or temperatures[0] == temperatures[1]):
        raise ValueError('supply exactly two distinct confirmed supported temperatures')
    base = RunConfig(model=model)
    configs = [base]
    if second_model:
        configs += [RunConfig(model=second_model), base]
    if temperatures:
        t1, t2 = (RunConfig(model=model, temperature=t) for t in temperatures)
        configs += [t1, t2, t1]
        if second_model:
            configs += [RunConfig(model=second_model, temperature=t) for t in temperatures]
    report = {'status': 'failed', 'scope': 'optional_matrix' if second_model or temperatures else 'single_checkpoint_readiness',
              'phase20': 'pending_real_matrix_and_independent_verification',
              'runtime': {'python': platform.python_version(), 'platform': platform.platform()},
              'calls': [], 'reuse': {}, 'limitations': [
                  'Semantic answers are observations, not pass/fail labels.',
                  'Different model names do not prove distinct checkpoints.',
                  'This command does not perform actual Claude harness delivery.']}
    try:
        report['runtime']['laya_mlx_version'] = importlib.metadata.version('laya_mlx')
    except importlib.metadata.PackageNotFoundError:
        report['runtime']['laya_mlx_version'] = None
    captures = []
    class CapturingAgent:
        def __init__(self, agent, config):
            self.agent, self.config = agent, config
        def predict(self, text, questions, **kwargs):
            record = {'requested': self.config.to_dict(), 'observed': observe(self.agent),
                      'text': text, 'questions': deepcopy(questions)}
            captures.append(record)
            raw = self.agent.predict(text, questions, **kwargs)
            try:
                json.dumps(raw, allow_nan=False)
                record['raw'] = deepcopy(raw)
            except (TypeError, ValueError):
                record['raw_representation'] = repr(raw)[:16384]
                record['raw_capture_limitation'] = 'Non-JSON response; bounded diagnostic representation only.'
            return raw
    def capture_loader(checkpoint, **kwargs):
        config = next(c for c in configs if c.model == checkpoint and c.load_kwargs() == kwargs)
        return CapturingAgent(loader(checkpoint, **kwargs), config)
    registry = AgentRegistry(loader=capture_loader)
    policies = {name: RulesConfig(name, conditions=[]) for name in QUESTIONS}
    rejecting = {name: RulesConfig(name, conditions=[{'field': 'readiness_missing_field', 'op': 'gte', 'value': 0}]) for name in QUESTIONS}
    def call(config, active_registry):
        raw = predict(TEXT, QUESTIONS, config=config, registry=active_registry)
        record = captures[-1]
        record.update(enriched=enrich_response({'answers': {name: raw['answers'][name] for name in QUESTIONS}}), decisions=interpret(raw, QUESTIONS, policies),
                      rejected=interpret(raw, QUESTIONS, rejecting))
        check_processing(raw, record['enriched'], record['decisions'], record['rejected'])
        report['calls'].append(record)
    try:
        first_agents = {}
        for config in configs:
            agent = registry.get_agent(config)
            if config in first_agents:
                report['reuse'][str(config.to_dict())] = agent is first_agents[config]
            first_agents[config] = agent
            call(config, registry)
        fresh = AgentRegistry(loader=capture_loader)
        report['reuse']['fresh_registry_new_object'] = fresh.get_agent(base).agent is not registry.get_agent(base).agent
        call(base, fresh)
        with TemporaryDirectory(prefix='laya-readiness-') as directory:
            root = Path(directory)
            (root / 'sample.ts').write_text(SOURCE, encoding='utf-8')
            flow = run_flow('Explain `sample.ts`: how does double work?', cwd=root, repository_root=root,
                            config=base, registry=registry)
            if flow['status'] == 'context' and flow['context']['code'] != SOURCE:
                raise ValueError('flow selected source differs from synthetic fixture')
            if flow['status'] == 'noop' and flow['reason'] not in ('method_undecided', 'no_single_match', 'multiple_undecided', 'multiple_relevant'):
                raise ValueError(f'flow compatibility failure: {flow["reason"]}')
            # Temporary absolute paths are not useful for returned evidence.
            report['flow'] = json.loads(json.dumps(flow).replace(str(root), '<synthetic-project>'))
        report['flow_calls'] = captures[len(report['calls']):]
        if not all(report['reuse'].values()):
            raise ValueError('agent reuse/fresh-registry contract failed')
        report['status'] = 'passed_preparation_probe'
    except Exception as exc:
        report['error'] = f'{type(exc).__name__}: {exc}'
        report['calls'] = captures
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--real', action='store_true', help='explicitly permit SDK loading and inference')
    parser.add_argument('--output', required=True, type=Path, help='new local JSON evidence file (review before sharing)')
    parser.add_argument('--model', default=RunConfig().model)
    parser.add_argument('--second-model', help='distinct checkpoint confirmed compatible by the user')
    parser.add_argument('--temperature', type=float, action='append', default=[], help='repeat twice, using confirmed supported values')
    args = parser.parse_args(argv)
    if not args.real or platform.system() != 'Darwin' or platform.machine() != 'arm64':
        print('BLOCKED: --real and a supported Apple Silicon Mac environment are required.', file=sys.stderr)
        return 2
    if args.output.exists():
        print('BLOCKED: choose a new output path; existing evidence is never overwritten.', file=sys.stderr)
        return 2
    try:
        # SDK chatter is diagnostic; the structured evidence is written only to the selected file.
        with redirect_stdout(sys.stderr):
            report = run_check(loader=real_loader, model=args.model, second_model=args.second_model,
                               temperatures=args.temperature)
        encoded = json.dumps(report, indent=2, allow_nan=False) + '\n'
        with args.output.open('x', encoding='utf-8') as handle:
            handle.write(encoded)
    except (TypeError, ValueError, OSError) as exc:
        print(f'BLOCKED: {exc}', file=sys.stderr)
        return 2
    print(f'{report["status"]}: {args.output}')
    return 0 if report['status'] == 'passed_preparation_probe' else 1


if __name__ == '__main__':
    raise SystemExit(main())
