"""Pure recovery event policy; existing session bridge owns all persistence."""
from dataclasses import dataclass
from pathlib import Path

SOURCE = {'kind': 'flow', 'name': 'subagent_test_recovery'}
ASSIGNMENT = 'test_assignment_identified'
ENRICHMENT = 'private_method_test_guidance_enriched'


class RecoveryStateError(ValueError):
    """Invalid or ambiguous recovery state; callers diagnose and no-op."""


def _text(value):
    if not isinstance(value, str) or not value.strip():
        raise RecoveryStateError('expected_nonblank_string')


@dataclass(frozen=True)
class RecoveryTarget:
    file_path: str
    owner_kind: str
    class_name: str | None
    method_name: str
    signature: str

    def __post_init__(self):
        for value in (self.file_path, self.method_name, self.signature):
            _text(value)
        if not Path(self.file_path).is_absolute():
            raise RecoveryStateError('expected_absolute_file')
        if self.owner_kind == 'class':
            _text(self.class_name)
        elif self.owner_kind != 'function' or self.class_name is not None:
            raise RecoveryStateError('invalid_owner')


@dataclass(frozen=True)
class TrackedAssignment:
    session_id: str
    tool_use_id: str
    agent_id: str | None
    target: RecoveryTarget

    def __post_init__(self):
        _text(self.session_id)
        _text(self.tool_use_id)
        if self.agent_id is not None:
            _text(self.agent_id)
        if not isinstance(self.target, RecoveryTarget):
            raise RecoveryStateError('invalid_target')


@dataclass(frozen=True)
class RecoveryStateDecision:
    allow: bool
    reason: str
    matched_event_index: int | None = None


def _payload(assignment):
    if not isinstance(assignment, TrackedAssignment):
        raise RecoveryStateError('invalid_assignment')
    target = assignment.target
    return {'schemaVersion': 1, 'sessionId': assignment.session_id,
            'toolUseId': assignment.tool_use_id, 'agentId': assignment.agent_id,
            'target': {'filePath': target.file_path, 'ownerKind': target.owner_kind,
                       'className': target.class_name, 'methodName': target.method_name,
                       'signature': target.signature}}


def build_assignment_event(assignment):
    return {'source': dict(SOURCE), 'type': ASSIGNMENT, 'payload': _payload(assignment)}


def build_enrichment_event(assignment, *, agent_id):
    _text(agent_id)
    if not isinstance(assignment, TrackedAssignment):
        raise RecoveryStateError('invalid_assignment')
    if assignment.agent_id is not None and assignment.agent_id != agent_id:
        raise RecoveryStateError('conflicting_agent')
    payload = _payload(assignment)
    payload.update(agentId=agent_id, blocker='private_method')
    return {'source': dict(SOURCE), 'type': ENRICHMENT, 'payload': payload}


def _events(history, session_id):
    _text(session_id)
    if not isinstance(history, list):
        raise RecoveryStateError('invalid_history')
    for index, event in enumerate(history):
        if not isinstance(event, dict):
            raise RecoveryStateError('invalid_history_event')
        if event.get('source') != SOURCE or event.get('type') not in (ASSIGNMENT, ENRICHMENT):
            continue
        payload = event.get('payload')
        try:
            if not isinstance(payload, dict) or type(payload.get('schemaVersion')) is not int or payload['schemaVersion'] != 1:
                raise RecoveryStateError('invalid_schema')
            target = payload['target']
            if not isinstance(target, dict):
                raise RecoveryStateError('invalid_target')
            assignment = TrackedAssignment(payload['sessionId'], payload['toolUseId'], payload['agentId'],
                RecoveryTarget(target['filePath'], target['ownerKind'], target['className'],
                               target['methodName'], target['signature']))
            if assignment.session_id != session_id:
                raise RecoveryStateError('session_mismatch')
            if event['type'] == ENRICHMENT:
                _text(assignment.agent_id)
                if payload.get('blocker') != 'private_method':
                    raise RecoveryStateError('invalid_blocker')
        except (KeyError, TypeError) as exc:
            raise RecoveryStateError('invalid_recovery_event') from exc
        yield index, event['type'], assignment


def find_assignment(history, *, session_id, tool_use_id, agent_id):
    _text(tool_use_id)
    _text(agent_id)
    found = None
    for _, kind, stored in _events(history, session_id):
        if kind != ASSIGNMENT or stored.tool_use_id != tool_use_id:
            continue
        if found is not None and found != stored:
            raise RecoveryStateError('conflicting_assignment')
        found = stored
    if found is None:
        return None
    if found.agent_id is not None and found.agent_id != agent_id:
        raise RecoveryStateError('conflicting_agent')
    return TrackedAssignment(found.session_id, found.tool_use_id, agent_id, found.target)


def has_enrichment(history, *, session_id, agent_id):
    _text(agent_id)
    # Exhaust validation even when an earlier matching event was found.
    events = list(_events(history, session_id))
    return any(kind == ENRICHMENT and assignment.agent_id == agent_id
               for _, kind, assignment in events)


def decide_enrichment(history, assignment, *, agent_id):
    if not isinstance(assignment, TrackedAssignment):
        raise RecoveryStateError('invalid_assignment')
    build_enrichment_event(assignment, agent_id=agent_id)
    current = find_assignment(history, session_id=assignment.session_id,
                              tool_use_id=assignment.tool_use_id, agent_id=agent_id)
    if current is None:
        return RecoveryStateDecision(False, 'assignment_missing'), None
    if current.target != assignment.target:
        raise RecoveryStateError('stale_assignment')
    if has_enrichment(history, session_id=assignment.session_id, agent_id=agent_id):
        index = next(index for index, kind, stored in _events(history, assignment.session_id)
                     if kind == ENRICHMENT and stored.agent_id == agent_id)
        return RecoveryStateDecision(False, 'already_enriched', index), None
    return RecoveryStateDecision(True, 'enrich'), build_enrichment_event(current, agent_id=agent_id)
