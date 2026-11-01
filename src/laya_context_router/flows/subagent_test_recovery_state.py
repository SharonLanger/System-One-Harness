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
