from time import monotonic

from hooks.contracts import Noop
from hooks.post_compact.dispatcher import dispatch_post_compact
from tests.support.memory_session_store import MemorySessionStore


def test_post_compact_saves_through_injected_store():
    from types import SimpleNamespace

    store = MemorySessionStore()
    envelope = SimpleNamespace(common={'session_id': 's'}, raw_payload={'trigger': 'manual'})
    args = SimpleNamespace(log_state=True, deadline_at=monotonic() + 10)
    result = dispatch_post_compact(envelope, args, lambda *a, **kw: None, session_store=store)
    assert isinstance(result, Noop)
    assert [e['type'] for e in store.events['s']] == ['PostCompact']
    assert store.events['s'][0]['payload'] == {}
