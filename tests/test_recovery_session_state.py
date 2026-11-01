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
