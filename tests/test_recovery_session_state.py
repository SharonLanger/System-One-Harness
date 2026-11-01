import pytest
from laya_context_router.flows.subagent_test_recovery_state import (
    RecoveryTarget, TrackedAssignment, RecoveryStateError,
    build_assignment_event, build_enrichment_event,
)


def assignment(tool='tool-1', agent=None, session='session-1', name='normalize'):
    return TrackedAssignment(session, tool, agent,
        RecoveryTarget('/project/service.ts', 'class', 'Service', name, name+'(x: string): string'))


def test_builders_detached_and_exact():
    a = assignment()
    event = build_assignment_event(a)
    assert set(event) == {'source', 'type', 'payload'}
    assert event['type'] == 'test_assignment_identified'
    assert event['payload'] == {'schemaVersion': 1, 'sessionId': 'session-1',
        'toolUseId': 'tool-1', 'agentId': None, 'target': {
        'filePath': '/project/service.ts', 'ownerKind': 'class', 'className': 'Service',
        'methodName': 'normalize', 'signature': 'normalize(x: string): string'}}
    event['source']['name'] = 'changed'
    event['payload']['target']['methodName'] = 'changed'
    enriched = build_enrichment_event(a, agent_id='child')
    assert enriched['source']['name'] == 'subagent_test_recovery'
    assert enriched['payload']['target']['methodName'] == 'normalize'
    assert enriched['payload']['blocker'] == 'private_method'
    assert enriched['payload']['agentId'] == 'child'
    assert 'timestamp' not in enriched


@pytest.mark.parametrize('field,value', [('file_path','relative.ts'),('file_path',' '),
    ('method_name',''),('signature',3),('owner_kind','unknown'),('class_name',None)])
def test_invalid_target(field, value):
    values=dict(file_path='/a.ts', owner_kind='class', class_name='A', method_name='m', signature='m()')
    values[field]=value
    with pytest.raises(RecoveryStateError): RecoveryTarget(**values)


def test_function_owner():
    assert RecoveryTarget('/a.ts','function',None,'f','f()').class_name is None
    with pytest.raises(RecoveryStateError): RecoveryTarget('/a.ts','function','A','f','f()')


@pytest.mark.parametrize('agent', ['', ' ', 1, None])
def test_enrichment_requires_actual_child(agent):
    with pytest.raises(RecoveryStateError): build_enrichment_event(assignment(),agent_id=agent)


def test_conflicting_child_and_invalid_ids():
    with pytest.raises(RecoveryStateError): build_enrichment_event(assignment(agent='one'),agent_id='two')
    with pytest.raises(RecoveryStateError): assignment(tool='')
    with pytest.raises(RecoveryStateError): assignment(session=' ')

from copy import deepcopy
from laya_context_router.flows.subagent_test_recovery_state import find_assignment, has_enrichment


def lookup(history, tool='tool-1', agent='child', session='session-1'):
    return find_assignment(history,session_id=session,tool_use_id=tool,agent_id=agent)


def test_lookup_binds_without_mutation_and_ignores_timestamps():
    event=build_assignment_event(assignment()); history=[event,deepcopy(event)]
    history[0]['timestamp']='later'; history[1]['timestamp']='earlier'
    original=deepcopy(history)
    assert lookup(history).agent_id=='child'
    assert history==original
    assert lookup(history,tool='other') is None


@pytest.mark.parametrize('other', [assignment(agent='child'), assignment(name='other')])
def test_conflicting_records(other):
    with pytest.raises(RecoveryStateError): lookup([build_assignment_event(assignment()),build_assignment_event(other)])


def test_child_conflict():
    with pytest.raises(RecoveryStateError): lookup([build_assignment_event(assignment(agent='other'))])


def test_independent_invocations_and_agents():
    history=[build_assignment_event(assignment()),build_assignment_event(assignment(tool='tool-2'))]
    assert lookup(history).tool_use_id=='tool-1'
    assert lookup(history,tool='tool-2',agent='other').agent_id=='other'
    history.append(build_enrichment_event(assignment(),agent_id='child'))
    history.append({'source':{'kind':'hook','name':'PostCompact'},'type':'PostCompact','payload':{}})
    assert has_enrichment(history,session_id='session-1',agent_id='child')
    assert not has_enrichment(history,session_id='session-1',agent_id='other')


@pytest.mark.parametrize('change', ['version','target','session','agent','blocker'])
def test_malformed_recognized_history_rejected(change):
    event=build_enrichment_event(assignment(tool='other'),agent_id='other')
    if change=='version': event['payload']['schemaVersion']=True
    elif change=='target': del event['payload']['target']['signature']
    elif change=='session': event['payload']['sessionId']='other'
    elif change=='agent': event['payload']['agentId']=None
    else: event['payload']['blocker']='other'
    with pytest.raises(RecoveryStateError): lookup([event])
    with pytest.raises(RecoveryStateError): has_enrichment([event],session_id='session-1',agent_id='child')


def test_unrelated_events_ignored_and_empty_history():
    history=[{'source':{'kind':'hook','name':'PostCompact'},'type':'PostCompact'},
             {'source':{'kind':'flow','name':'subagent_test_recovery'},'type':'future_event'}]
    assert lookup(history) is None
    assert not has_enrichment([],session_id='session-1',agent_id='child')
