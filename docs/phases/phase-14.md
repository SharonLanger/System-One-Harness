# Phase 14 — bounded flow composition

Starting commit: 8a46ea56ea75dad5ed4ad37e2566d5ec58123da6; Python3.12,
Node24, pinned TypeScript5.9.3. Independent planner/reviewer:
`/root/flow_builder/phase_reviews` (Luna medium).

Scope: optional `fallback_config` enables exactly one further method-selection
call only when method policy rejects and multiple_relevant is accepted `no`.
First-round payload is unchanged. The second text appends the fixed source
snapshot ID/signature list; question choices and source mapping stay unchanged.
`fallback_max_input_chars` independently bounds text plus compact questions JSON;
no truncation. Both rounds have explicit budgets, hence at most their sum.
Invalid second budget returns safe no-op before source/model work.
Default None disables this unevaluated representation experiment. No accuracy or
benefit claim. Explicit abstention/multiple/unclear-multi, failures and second
rejections terminate without retry. The same invocation registry handles configs.

Independent plan: exact sequence at SDK boundary, positive/rejected/abstained/error
second responses, disabled baseline, explicit terminal outcomes, exact budget
edge and invalid budgets, actual distinct blocks with policy divergence and A/B/A
identity reuse. Expected results follow declared rules and manually written
responses, never a production function generating its own expected decision.

TDD: new tests first ran 17 failed /1 passed (missing fallback keyword).
Existing tests/expectations unchanged. Added tests/test_flow_branches.py; changed
flow only; README/progress document optional behavior. Baseline full accumulated
suite:272 Python +6 Node passed, fresh build/typecheck. Final implementer serialized build/typecheck +6 Node +290 Python passed (34.90s Python); zero skips/xfail.

All agents/models/settings are explicitly simulated: A(.2/fr), B(.7/en), A reused.
The real adapter, block question construction, JSON validation, enrichment, named
policies, selection, Node parser and extraction execute; only SDK boundary mocked.
Two real distinct block identities (method_selection and ticket_triage) compose:
confidence .8 passes method policy .3 and fails department policy .9, churn's own
policy still accepts. Full expected requests/config kwargs and response ordering
are asserted. No SDK/harness installed, imported or activated.

Real Laya compatibility deferred/blocked until Phase20 on supported hardware;
model selection quality and fallback benefit remain unmeasured. Candidate evidence
2026-10-29. During initial concurrent validation, implementer saw3 failures
and reviewer saw3 failures, all MODULE_NOT_FOUND typescript during helper startup.
Reviewer had run npm ci concurrently on the shared dependency directory. Astra
high `/root/flow_builder/source_repairs` independently inspected installed npm ci:
it removes node_modules entries before reinstallation; helper requires TypeScript
before request/flow handling. Classified environmental race, no product repair
justified. No assertion, timeout, expectation or scope changed. Validation now
serializes dependency/build operations and suites; reviewer first isolated rerun
passed290 Python +6 Node, then implementer's final run above passed. Final
independent repeated serialized build/typecheck +6 Node +290 Python passed
(33.90s Python), zero skips/xfail. Reviewer inspected actual tracked/untracked
diff and mapped every stated requirement to executed tests. Verdict: VERIFIED
for stated Phase14 mock scope. Decision: COMPLETE.
