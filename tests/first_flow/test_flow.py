"""Root gates, authoritative block routing, and real one-hop source assembly."""
from copy import deepcopy
from dataclasses import replace
import builtins
import pytest

from conftest import FIXTURES, METHOD, PROMPT, SELECTED
from laya_context_router.block_runtime import BlockResult
from laya_context_router.building_blocks import typescript as ts
from laya_context_router.building_blocks.questions.requested_action import block as action
from laya_context_router.flows import first_method_context as flow
from laya_context_router.hooks.contracts import Context, Failure, Noop


def snapshot(root):
    return {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()}


def test_S01_S02_project_is_read_only_and_experiments_unavailable(h, monkeypatch, golden):
    project, fixture = snapshot(h.root), snapshot(FIXTURES / 'first_flow_project')
    original = builtins.__import__
    def no_experiment(name, *args, **kwargs):
        assert not name.startswith('experiments')
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', no_experiment)
    real_open = builtins.open
    def no_experiment_file(file, *args, **kwargs):
        assert 'experiments' not in str(file).split('/')
        return real_open(file, *args, **kwargs)
    monkeypatch.setattr(builtins, 'open', no_experiment_file)
    assert h.run() == Context(golden)
    assert h.run('Explain an algorithm') == Noop('no_file')
    assert project == snapshot(h.root)
    assert fixture == snapshot(FIXTURES / 'first_flow_project')


def test_S03_unmocked_public_block_hits_tripwire(h, monkeypatch):
    # This explicit harness check proves a missing block replacement is detected.
    from importlib import reload
    real = reload(action).run
    from laya_context_router.laya.registry import AgentRegistry
    with pytest.raises(AssertionError, match='real model/tokenizer'):
        real({'prompt': 'Explain work'}, config=h.config, registry=AgentRegistry(real=True))
    monkeypatch.setattr(action, 'run', h.action)


def test_S04_inputs_and_block_results_are_not_mutated(h, golden):
    request = h.request(config='config.json')
    (h.root / 'config.json').write_text('{"model":"offline-fixed-blocks"}')
    before = deepcopy((request, h.action_result, h.selection_result, h.outline))
    assert flow.handle_prompt(request, h.logger, registry=h.registry) == Context(golden)
    assert (request, h.action_result, h.selection_result, h.outline) == before


def test_P01_R01_normal_order_counts_root_and_unmodified_prompts(h, monkeypatch, golden):
    order, resolutions = [], []
    for name in ('outline', 'extract_callable', 'get_called_method_locations'):
        real = getattr(ts, name)
        def spy(*args, _name=name, _real=real, **kwargs):
            order.append((_name, args, kwargs))
            return _real(*args, **kwargs)
        monkeypatch.setattr(ts, name, spy)
    real_resolve = flow.resolve_file
    def resolving(*args, **kwargs):
        resolutions.append(kwargs)
        return real_resolve(*args, **kwargs)
    monkeypatch.setattr(flow, 'resolve_file', resolving)
    assert h.run() == Context(golden)
    assert [x[0] for x in order] == ['outline', 'extract_callable', 'get_called_method_locations', 'outline']
    assert resolutions == [{'cwd': h.root, 'repository_root': h.root, 'resolve_from_project_root': True}]
    assert [c[0] for c in h.calls] == ['action', 'selection']
    assert h.calls[0][1] == {'prompt': PROMPT}
    assert h.calls[1][1] == {'text': PROMPT, 'source_outline': h.outline}
    assert all(c[2] == {'config': h.config, 'registry': h.registry} for c in h.calls)
    assert order[2][1] == (SELECTED, h.candidate['id'])
    assert order[2][2] == {'project_root': h.root}


@pytest.mark.parametrize('where', ['subdirectory', 'decoy'])
def test_P02_process_and_event_cwd_do_not_choose_source(h, monkeypatch, tmp_path, golden, where):
    decoy = tmp_path / 'decoy'; decoy.mkdir()
    (decoy / 'config.json').write_text('{"model":"wrong"}')
    (decoy / 'invoice-service.ts').write_text('throw new Error("DO NOT EXECUTE");')
    cwd = h.root / 'src' if where == 'subdirectory' else decoy
    monkeypatch.chdir(cwd)
    request = h.request()
    request = replace(request, envelope=replace(request.envelope, common={**request.envelope.common, 'cwd': str(cwd)}))
    assert flow.handle_prompt(request, h.logger, registry=h.registry) == Context(golden)


@pytest.mark.parametrize('kind', ['absent', 'relative', 'missing', 'file'])
def test_P03_invalid_root_fails_before_config_source_or_blocks(h, monkeypatch, tmp_path, kind):
    root = {'absent': None, 'relative': 'relative', 'missing': str(tmp_path / 'missing'), 'file': str(h.path)}[kind]
    from laya_context_router.laya import config
    def forbidden(*args, **kwargs):
        pytest.fail('invalid root must prevent setup and source reads')
    monkeypatch.setattr(config, 'load_config', forbidden)
    monkeypatch.setattr(flow, 'detect_configured_references', forbidden)
    assert flow.handle_prompt(h.request(repository_root=root, config='/explicit/config'), h.logger) == Failure('invalid_project_root', 'configuration', 'repository_root')
    assert not h.calls


@pytest.mark.parametrize('absolute', [False, True])
def test_P04_config_is_explicitly_rooted_without_mutation(h, monkeypatch, tmp_path, golden, absolute):
    (h.root / 'config.json').write_text('{"model":"root-model"}')
    decoy = tmp_path / 'decoy'; decoy.mkdir()
    (decoy / 'config.json').write_text('{"model":"decoy-model"}')
    monkeypatch.chdir(decoy)
    request = h.request(config=str(h.root / 'config.json') if absolute else 'config.json')
    original = deepcopy(request)
    assert flow.handle_prompt(request, h.logger, registry=h.registry) == Context(golden)
    assert h.calls[0][2]['config'].model == 'root-model'
    assert request == original


@pytest.mark.parametrize('prompt', ['', ' \n ', 'Explain algorithms', 'Explain `source.js`'])
def test_P05_blank_no_reference_and_unsupported_extension(h, prompt):
    assert isinstance(h.run(prompt), Noop)
    assert not h.calls and not h.prepared()


@pytest.mark.parametrize('suffix', ['.spec.ts', '.test.ts', '.d.ts'])
def test_P06_lexical_and_canonical_exclusions(h, suffix):
    target = h.root / ('excluded' + suffix)
    target.write_text('export function hidden() {}')
    alias = h.root / 'alias.ts'; alias.symlink_to(target)
    for path in [target.name, alias.name]:
        assert h.run(f'Explain `{path}`') == Noop('excluded')
    assert not h.calls


def test_P07_repeated_spellings_and_symlinks_deduplicate(h, golden):
    (h.root / 'alias.ts').symlink_to(h.path)
    result = h.run(f'Explain `{SELECTED}` and `./{SELECTED}` and `alias.ts` and `{SELECTED}`')
    assert result == Context(golden)
    assert [x[0] for x in h.calls] == ['action', 'selection']


@pytest.mark.parametrize('second', ['tests/invoice-service.spec.ts', 'missing.ts', 'src/utils/rounding.ts'])
def test_P08_never_discard_second_recognized_reference(h, second):
    assert h.run(f'Explain `{SELECTED}` and `{second}`') == Noop('multiple_files')
    assert not h.calls


@pytest.mark.parametrize('kind', ['missing', 'ambiguous'])
def test_P09_resolver_outcome_is_authoritative(h, kind):
    if kind == 'ambiguous':
        for folder in ['one', 'two']:
            directory = h.root / folder; directory.mkdir()
            (directory / 'same.ts').write_text('function same() {}')
    prompt = 'Explain `same.ts`' if kind == 'ambiguous' else 'Explain `missing.ts`'
    assert h.run(prompt) == Noop(kind)
    assert not h.calls


@pytest.mark.parametrize('status', ['inaccessible', 'not_file', 'invalid_resolution_mode', 'unknown', 'resolved'])
def test_P09_resolution_errors_and_contract_failures_are_failures(h, monkeypatch, status):
    from laya_context_router.building_blocks.resolve_file import Resolution
    monkeypatch.setattr(flow, 'resolve_file', lambda *args, **kwargs: Resolution(status))
    expected = status if status in {'inaccessible', 'not_file', 'invalid_resolution_mode'} else 'invalid_resolution_result'
    assert h.run() == Failure(expected, 'resolution')
    assert not h.calls


@pytest.mark.parametrize('kind', ['absolute', 'traversal', 'symlink'])
def test_P10_outside_root_is_never_extracted(h, tmp_path, kind):
    outside = tmp_path / 'outside.ts'; outside.write_text('function outside() {}')
    alias = h.root / 'outside.ts'; alias.symlink_to(outside)
    ref = {'absolute': str(outside), 'traversal': '../outside.ts', 'symlink': 'outside.ts'}[kind]
    result = h.run(f'Explain `{ref}`')
    assert result == Failure('outside_repository', 'resolution')
    assert not h.calls and not h.prepared()


def test_R02_generate_tests_uses_same_source_policy(h, golden):
    h.action_result.data['action'] = 'generate_tests'
    assert h.run() == Context(golden)


@pytest.mark.parametrize('value', ['modify_code', 'undecided', 'skip'])
def test_R03_R04_stop_after_authoritative_action(h, monkeypatch, value):
    if value == 'skip':
        h.action_result = BlockResult('skipped', 'input_budget_exceeded', {}, {})
    else:
        h.action_result.data['action'] = value
    def forbidden(*args, **kwargs):
        pytest.fail('outline must not run')
    monkeypatch.setattr(ts, 'outline', forbidden)
    assert h.run() == Noop('input_budget_exceeded' if value == 'skip' else value)
    assert [x[0] for x in h.calls] == ['action']


def test_R05_real_empty_outline_stops_selection(h):
    h.path.write_text('export const value = 1;')
    assert h.run() == Noop('no_candidates')
    assert [x[0] for x in h.calls] == ['action']


@pytest.mark.parametrize('reason', ['no_single_match', 'method_undecided', 'multiple_relevant', 'multiple_undecided', 'candidate_budget_exceeded', 'input_budget_exceeded'])
@pytest.mark.parametrize('skipped', [False, True])
def test_R06_T07_declared_selection_nonselection_and_local_budgets(h, monkeypatch, reason, skipped):
    h.selection_result.data.update(selected_id=None, reason=reason)
    if skipped:
        h.selection_result.status = 'skipped'; h.selection_result.reason = reason
    def forbidden(*args, **kwargs):
        pytest.fail('extraction must not run')
    monkeypatch.setattr(ts, 'extract_callable', forbidden)
    assert h.run() == Noop(reason)
    assert len(h.calls) == 2
    assert reason not in str(h.prepared())


def test_R07_T06_answers_control_routing_without_confidence_reinterpretation(h, golden):
    h.action_result.decisions = {'requested_action': {'answer': 'modify_code', 'confidence': 0}}
    h.selection_result.decisions = {'method': {'decided': False, 'confidence': 0}}
    assert h.run() == Context(golden)
    assert [d['token_metadata'] for _, event, d in h.logs if event == 'block_finished'] == ['unavailable', 'unavailable']


def test_R08_duplicate_names_use_exact_selected_identity(h):
    h.path.write_text('class First { work() { return "FIRST"; } }\nclass Second { work() { return "SECOND"; } }')
    h.choose('work', index=1)
    result = h.run()
    assert isinstance(result, Context)
    assert 'return "SECOND"' in result.text and 'FIRST' not in result.text
    assert h.candidate['id'] not in result.text


@pytest.mark.parametrize('kind', ['action', 'selection', 'transport'])
def test_R09_malformed_result_does_not_choose_substitute(h, kind):
    if kind == 'action':
        h.action_result.data['action'] = 'invented'
    elif kind == 'transport':
        h.action_result = {'action': 'explain'}
    else:
        h.selection_result.data['selected_id'] = 'unknown-id'
    result = h.run()
    assert isinstance(result, Failure)
    assert not h.prepared()


@pytest.mark.parametrize('stage', ['action', 'selection'])
@pytest.mark.parametrize('error', [RuntimeError, TimeoutError])
def test_R10_block_error_stops_or_propagates_deadline(h, stage, error):
    setattr(h, stage + '_result', error('planned'))
    if error is TimeoutError:
        with pytest.raises(TimeoutError):
            h.run()
    else:
        assert h.run() == Failure('block_error', 'requested_action' if stage == 'action' else 'method_selection', message='RuntimeError')
    assert len(h.calls) == (1 if stage == 'action' else 2)
    assert not h.prepared()


def test_N02_N03_direct_only_deduplicated_targets_no_bodies(h):
    (h.root / 'target.ts').write_text('export function direct() { return deeper(); }\nfunction deeper() { return "TRANSITIVE_BODY"; }')
    h.path.write_text('import {direct} from "../../target";\nexport function chosen() { direct(); direct(); }\nfunction incoming() { chosen(); }')
    h.choose('chosen')
    result = h.run()
    assert isinstance(result, Context)
    assert result.text.count('target.ts | export function direct() | Lines: 1–1') == 1
    assert all(x not in result.text for x in ['deeper', 'incoming', 'TRANSITIVE_BODY'])


def test_N04_no_project_callees_keeps_method(h):
    h.path.write_text('export function chosen() { return 3; }')
    h.choose('chosen')
    result = h.run()
    assert isinstance(result, Context)
    assert 'return 3;' in result.text
    assert 'No project methods were reported.' in result.text


def test_N05_partial_preserves_real_navigation_entries(h, monkeypatch):
    h.path.write_text(h.path.read_text().replace(
        '  const base = calculateInvoiceTotal(invoice);',
        '  unresolved();\n  const base = calculateInvoiceTotal(invoice);'))
    h.choose(METHOD)
    real = ts.get_called_method_locations
    reported = []
    def partial(*args, **kwargs):
        result = real(*args, **kwargs)
        reported.append(deepcopy(result))
        return result
    monkeypatch.setattr(ts, 'get_called_method_locations', partial)
    result = h.run()
    assert isinstance(result, Context)
    assert reported[0]['status'] == 'partial'
    assert any(d['code'] == 'unresolved_target' for d in reported[0]['diagnostics'])
    assert 'calculateInvoiceTotal(invoice: Invoice)' in result.text
    assert 'roundToCents(value: number)' in result.text
    assert 'Call list is partial; some targets could not be resolved.' in result.text
    assert all(d['message'] not in result.text for d in reported[0]['diagnostics'])


@pytest.mark.parametrize('kind', ['exception', 'error_result', 'timeout'])
def test_N06_navigation_failure_keeps_only_method_except_deadline(h, monkeypatch, kind):
    def failed(*args, **kwargs):
        if kind == 'error_result':
            return {'status': 'error', 'data': None, 'diagnostics': [{'code': 'error', 'message': 'RAW_ERROR'}]}
        raise (TimeoutError if kind == 'timeout' else RuntimeError)('RAW_ERROR')
    monkeypatch.setattr(ts, 'get_called_method_locations', failed)
    if kind == 'timeout':
        with pytest.raises(TimeoutError):
            h.run()
    else:
        result = h.run()
        assert isinstance(result, Context)
        assert 'Call list unavailable.' in result.text
        assert 'RAW_ERROR' not in result.text
        assert 'roundToCents(value: number)' not in result.text


@pytest.mark.parametrize('moment', ['before_extraction', 'after_navigation', 'removed'])
def test_N07_stale_or_missing_selected_snapshot_never_emits(h, monkeypatch, moment):
    if moment == 'before_extraction':
        real = h.selection
        def changing(*args, **kwargs):
            result = real(*args, **kwargs)
            h.path.write_text(h.path.read_text() + '\n// concurrent edit')
            return result
        from laya_context_router.building_blocks.questions.method_selection_v2 import block
        monkeypatch.setattr(block, 'run', changing)
    else:
        real = ts.get_called_method_locations
        def changing(*args, **kwargs):
            result = real(*args, **kwargs)
            if moment == 'removed':
                h.path.unlink()
            else:
                h.path.write_text(h.path.read_text() + '\n// concurrent edit')
            return result
        monkeypatch.setattr(ts, 'get_called_method_locations', changing)
    assert isinstance(h.run(), Failure)
    assert not h.prepared()
