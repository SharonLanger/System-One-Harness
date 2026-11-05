from copy import deepcopy
from dataclasses import replace
import pytest
from flows.first_method_context_utils import SelectedMethod, build_enrichment_event, decide_enrichment

S = SelectedMethod('/project/Unicode Ω/orders.ts', 'calculate', 'calculate(): number', 20, 45)
C = {'source': {'kind': 'hook', 'name': 'PostCompact'}, 'type': 'PostCompact', 'payload': {}}


def event(s=S):
    return build_enrichment_event(s)


@pytest.mark.parametrize('history,allow,reason', [
    ([], True, 'no_history'),
    ([event()], False, 'already_enriched_since_compaction'),
    ([event(), {'source': {'kind': 'flow', 'name': 'other'}}], False, 'already_enriched_since_compaction'),
    ([event(), C], True, 'compaction_after_enrichment'),
    ([event(), C, event()], False, 'already_enriched_since_compaction'),
    ([event(), C, C], True, 'compaction_after_enrichment'),
    ([C, event()], False, 'already_enriched_since_compaction'),
])
def test_policy(history, allow, reason):
    before = deepcopy(history)
    decision = decide_enrichment(history, S)
    assert (decision.allow, decision.reason) == (allow, reason)
    assert history == before


@pytest.mark.parametrize('changes', [dict(file_path='/other/orders.ts'), dict(name='other'),
    dict(signature='calculate(x: number): number'), dict(start_line=21), dict(end_line=46)])
def test_distinct_identity(changes):
    assert decide_enrichment([event()], replace(S, **changes)).allow


@pytest.mark.parametrize('source,event_type', [({'kind':'flow','name':'PostCompact'}, 'PostCompact'),
    ({'kind':'hook','name':'PostCompact'}, 'other'), ({'kind':'hook','name':'other'}, 'PostCompact')])
def test_only_exact_compaction(source, event_type):
    assert not decide_enrichment([event(), dict(source=source, type=event_type)], S).allow


def test_other_flow_and_legacy_do_not_suppress():
    e = event(); e['source']['name'] = 'other'
    assert decide_enrichment([e], S).allow
    e = event(); del e['payload']['files'][0]['methods']
    d = decide_enrichment([e], S)
    assert d.allow and d.legacy_event_indices == (0,)


@pytest.mark.parametrize('bad', [None, [], {'methods': []}, {'filePath': S.file_path, 'methods': [None]},
    {'filePath': S.file_path, 'methods': [{'name': S.name, 'startLine': True}]}])
def test_malformed_metadata_ignored(bad):
    e = event(); e['payload']['files'] = [bad]
    assert decide_enrichment([e], S).allow


def test_payload_and_timestamps():
    e = event()
    assert 'timestamp' not in e
    f = e['payload']['files'][0]
    assert f['methodNames'] == [f['methods'][0]['name']] == [S.name]
    e['timestamp'] = '2099-01-01T00:00:00.000Z'
    c = deepcopy(C); c['timestamp'] = '2000-01-01T00:00:00.000Z'
    assert decide_enrichment([e, c], S).allow


@pytest.mark.parametrize('changes', [dict(file_path='relative.ts'), dict(name=''), dict(signature=''),
    dict(start_line=True), dict(start_line=0), dict(end_line=1)])
def test_invalid_summary(changes):
    with pytest.raises(ValueError):
        replace(S, **changes)
