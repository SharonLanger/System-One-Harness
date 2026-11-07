# Recovery session-state helpers

`flows/subagent_test_recovery_state.py` builds and interprets two pivotal events:
`test_assignment_identified` and `private_method_test_guidance_enriched`.
The existing TypeScript JSONL store supplies timestamps. Existing Python save/load
transactions, locking and paths remain unchanged.

```python
from laya_context_router.flows.subagent_test_recovery_state import (
    RecoveryTarget, TrackedAssignment, build_assignment_event, decide_enrichment,
)
from laya_context_router.hooks.session_state import save_event, inspect_and_save_event

# Inputs already resolved by the caller. Class methods require a class name;
# top-level functions use owner_kind='function' and class_name=None.
a = TrackedAssignment(session_id, tool_use_id, None,
    RecoveryTarget('/project/service.ts', 'class', 'Service', 'normalize',
                   'normalize(input: string): string'))
save_event(session_id, build_assignment_event(a), deadline=deadline)

# Later: resolve tool_use_id for the actual child, assess the response and prepare
# budget-compliant corrective guidance outside the lock. Then commit enrichment.
decision = inspect_and_save_event(session_id,
    lambda history: decide_enrichment(history, a, agent_id=actual_child_id),
    deadline=deadline)
# Return prepared guidance only after successful save and decision.allow is True.
```

`find_assignment` looks up an exact parent-session/tool invocation pair and binds
an unresolved child ID only in the returned immutable object. It does not alter
history. Missing assignment returns None; decide_enrichment returns a false
assignment_missing decision. `has_enrichment` checks parent-session/child identity
regardless of target, invocation, resume or compaction. Repeated identical prompt
text is valid new work; no prompt comparison or general deduplication exists.

Recognized recovery events are validated throughout the supplied session history.
Malformed payloads, unknown schema versions, wrong session identity and conflicting
assignment records raise RecoveryStateError. Unrelated sources/types are ignored.
Equivalent repeated assignment records are accepted. Astra clarified that stored
null and actual child IDs for one invocation are conflicting identities; compare
stored records before binding. No implicit reconciliation is performed.

The caller catches validation/storage failures, logs diagnostics and returns no-op.
These utilities do not repair state, retry, parse transcripts, load guidance, call
LAYA, serialize hooks or persist errors/skips. There are no attempt, reservation,
counter or delivery events. Assignment-to-child correlation is a deferred Python
utility contract; never infer it by timing, prompt similarity or record order.

Use inspect_and_save_event for the final enrichment check and append. Cooperating
Python callers share its session lock; direct TypeScript writers do not. Model
calls and guidance reads must remain outside the lock. State records commitment
to returning guidance, not acknowledged delivery: a crash after append can consume
the one enrichment even if no guidance reaches Claude.

## Verification

Tests cover pure contracts, history conflicts and identity, replay, compaction,
real existing Node store roundtrips, failure-to-no-op examples and synchronized
process races. No live model/hook recovery or transcript correlation is asserted.

This implementation follows the full session-state design, including the two
event types and five tested increments. The full recovery flow is separate work.
