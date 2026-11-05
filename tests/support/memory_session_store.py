"""Minimal session history for multi-invocation scenarios."""
from copy import deepcopy
from datetime import datetime, timezone


class MemorySessionStore:
    def __init__(self):
        self.events = {}

    def save_event(self, session_id, event, *, deadline):
        saved = deepcopy(event)
        saved['timestamp'] = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        self.events.setdefault(session_id, []).append(saved)
        return deepcopy(saved)

    def inspect_and_save_event(self, session_id, decide, *, deadline):
        decision, event = decide(deepcopy(self.events.get(session_id, [])))
        if decision.allow:
            self.save_event(session_id, event, deadline=deadline)
        return decision
