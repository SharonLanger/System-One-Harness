"""A real hook request, flow, blocks and session policy across invocations."""
from time import monotonic
from types import SimpleNamespace

from flows.first_method_context import handle_prompt
from hooks.contracts import Context, Noop
from hooks.dispatcher import ingest_common
from hooks.post_compact.dispatcher import dispatch_post_compact
from hooks.user_prompt_submit.dispatcher import dispatch_user_prompt_submit
from tests.support.fake_laya import ScriptedLaya, action_answer, method_answer
from tests.support.memory_session_store import MemorySessionStore
from tests.support.recording_logger import RecordingLogger


def test_prompt_duplicate_compaction_and_other_session(tmp_path, monkeypatch):
    import log_utils
    log_path = tmp_path / 'should-not-be-written.jsonl'
    monkeypatch.setattr(log_utils, 'LOG_PATH', log_path)
    (tmp_path / 'sample.ts').write_text('export function calculateTotal(value: number) { return value + 1; }\n')
    store = MemorySessionStore()
    logger = RecordingLogger()
    fake = ScriptedLaya(*(step for _ in range(4) for step in (action_answer, method_answer)))
    registry = fake.registry()
    args = SimpleNamespace(repository_root=str(tmp_path), real=True, config=None,
                           max_context_chars=8000, deadline_at=monotonic() + 30)

    def prompt(session):
        payload = {'hook_event_name': 'UserPromptSubmit', 'session_id': session,
                   'cwd': str(tmp_path), 'transcript_path': '/unused/transcript',
                   'prompt': 'Explain `sample.ts`: calculateTotal'}
        envelope = ingest_common(payload, 'offline-invocation')
        return dispatch_user_prompt_submit(envelope, args, logger,
            handler=lambda request, log: handle_prompt(request, log, registry=registry,
                                                        session_store=store))

    with logger.capture_shared():
        assert isinstance(prompt('first'), Context)
        assert prompt('first') == Noop('already_enriched_since_compaction')
        compact = {'hook_event_name': 'PostCompact', 'session_id': 'first',
                   'cwd': str(tmp_path), 'transcript_path': '/unused/transcript', 'trigger': 'manual'}
        compact_args = SimpleNamespace(log_state=True, deadline_at=monotonic() + 30)
        assert isinstance(dispatch_post_compact(ingest_common(compact, 'offline-invocation'),
                                                compact_args, logger, session_store=store), Noop)
        assert isinstance(prompt('first'), Context)
        assert isinstance(prompt('second'), Context)
    fake.assert_complete()
    assert [event['type'] for event in store.events['first']] == [
        'context_enriched', 'PostCompact', 'context_enriched']
    assert [event['type'] for event in store.events['second']] == ['context_enriched']
    assert not log_path.exists()
