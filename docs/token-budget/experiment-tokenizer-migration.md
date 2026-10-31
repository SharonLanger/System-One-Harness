# Experiment tokenizer migration proposal

Status: implementation authorized by Sharon’s later follow-plan instruction. The compatibility design is selected: legacy predict() plus explicit predict_strict(). Existing experiments will be restored to current main; experiment migration/runs are not part of this PR.
Date: 2026-10-31
Reference: PR #23, inspected implementation head cba25cc3893d581f0a0ef605e4d6f8199f1648c6.

## Goal and scope

Keep existing experiments, especially Batch V2, working. Describe a future, explicit migration for experiments that should measure and enforce token budgets before live model inference. Sharon runs the real experiments; this change only adds this document.

The current PR makes shared predict() inspection mandatory. Some old experiment wrappers expose only get_agent(), so reverting their inspection wiring alone would break calls. Batch V2 also replays stored responses through RecordedAgent, which has no tokenizer. Existing experiment edits remain in the PR; this document neither approves them nor restores them to main. Do not merge on the assumption that experiments are already unchanged or compatible.

## What an experiment needs

A live model already tokenizes input internally. Budget inspection needs access to the matching tokenizer before inference so it can count the actual request, including questions, options, instructions, and special tokens. A static model limit is the ceiling, not a way to count tokens.

Experiment code should delegate inspection to the shared registry/adapter. It should not implement tokenization, copy SDK code, download an independent vocabulary, or estimate tokens from characters. Use the tokenizer belonging to the loaded model and the supported shared request assembly.

The existing PR contract is:
- AgentRegistry.get_agent(config): load/reuse the agent.
- AgentRegistry.get_inspector(config): obtain the matching inspection capability.
- inspector.inspect(text, questions): inspect a request without model inference.
- InspectionUnavailable, InspectionFailed, and InputTokenBudgetExceeded: structured failures before inference.

Current provider qualification includes strict SDK/runtime fingerprints. The requested simplification to centralized model limits is separate pending work. This document does not claim that any arbitrary installed model is already supported.

## Compatibility decision required before implementation

Recommended design: preserve legacy predict() behavior and introduce explicit predict_strict() for enforced inspection. Both share prediction and answer-processing implementation; strict mode adds the pre-inference check. These names describe a proposal, not APIs already implemented.

Under this proposal, unchanged callers continue working. Live experiments can opt into strict mode in a separately reviewed migration. Missing inspection must fail an explicitly strict call; it must not silently fall back to unchecked inference.

Building blocks currently call shared predict(). A future migration must provide an explicit way to select strict prediction through the building-block call chain, not merely add get_inspector() to a wrapper. Keep the default backward compatible. Choose the smallest consistent public API during implementation and test propagation; do not discover the mode from class names, closure variables, or the presence of fake agents.

Alternative: retain mandatory inspection in predict() and migrate every caller, including a separate replay path. That requires approved experiment edits and cannot satisfy a requirement that experiments remain byte-for-byte unchanged. Do not choose this alternative silently.

Writing this proposal does not settle the public API decision or authorize changes to Batch V2.

## Required behavior by execution mode

| Mode | Tokenizer access | Required behavior |
| --- | --- | --- |
| Existing unchanged experiment | No new requirement under compatibility proposal | Preserve prior execution and output contracts |
| Opted-in live inference | Matching loaded model tokenizer via registry | Inspect the exact submitted payload; infer only if it fits |
| Saved-answer/rule replay | None | Reuse stored response; perform answer/rule processing without model loading or token inspection |
| Fixture mode and unit tests | Mock inspector/tokenizer only when inspection is under test | Deterministic results; no SDK/model/tokenizer downloads or real tokenization |

Replay success is not evidence that a request fits a model budget. Never fabricate a successful budget report for replay. A historical inspection report, if retained, describes the original live request only; it cannot certify a changed payload.

## Batch V2 migration design

1. Preserve current question/rule/configuration ordering, inference sharing, identifiers, resume behavior, existing output layout, and call limits.
2. For an explicitly strict live configuration, initialize the real registry and matching inspector within the existing configuration-error handling boundary. The current PR resolves the inspector outside the load try/except; future wiring must cover that failure too.
3. Let the live Boundary delegate get_inspector(config) to the same registry/configuration used for its underlying agent. Continue recording the payload and raw response without altering them.
4. Inspect immediately before each actual live inference, using the same prepared payload that inference receives. Reuse capability initialization, not a report for a different request.
5. Keep RecordedAgent/replay free of tokenizer requirements. Replaying a stored response should route through shared answer/rule processing or a clearly unchecked prediction path selected explicitly by the runner. It must not invoke the strict entry point.
6. Preserve fixture operation without real tokenizer support. Do not use the current synthetic fixture inspector as a claim of real budget validity.
7. Keep inspection duration separate from model inference duration if timing is reported. Do not silently redefine existing timing fields or output schemas; any additions require deliberate migration.

A replay-only execution must not initialize a model or inspector merely to consume saved responses. A resumed run with missing live records may still need its existing model-loading behavior to generate those records.

## Other callers and file-level follow-up

The following are inspection/migration targets, not permission to edit them now.

| Location | Future responsibility |
| --- | --- |
| experiments/batch_v2/engine.py | Explicit live versus replay routing, Boundary delegation, configuration and per-request error handling |
| experiments/batch_v2/fixture_inspection.py | Remove reliance on synthetic success reports in replay; review whether this added module is needed at all |
| experiments/batch_v2/checks/test_engine.py and test_replay_contracts.py | Mocked tests for compatibility, strict live path, replay, resume and error isolation |
| experiments/batch/run.py | Observed wrapper delegates inspection to its underlying registry only for approved strict migration |
| experiments/support.py and flow_method_context.py | Observation/capture wrappers forward capability without creating a second agent |
| experiments/block_method_selection.py | Preserve capture behavior; explicitly pass strict selection and matching inspection capability if migrated |
| experiments/block_v2_ticket_defaults.py, block_v2_ticket_overrides.py, experiment_runner.py, laya_choice.py | Forward approved strict selection through their existing call chain; no unrelated behavior changes |
| experiments/batch/checks/test_batch.py | Mock inspection at the boundary; preserve existing assertions |
| src/laya_context_router/laya/predict.py and registry.py | Implement the selected compatibility policy centrally |
| Shared building-block prediction call sites | Carry explicit strict selection to the prediction boundary while preserving existing defaults |

Before implementation, compare these paths with the then-current main branch. Preserve concurrent experiment work. Restoring prior PR edits must not overwrite newer main changes.

## Failure handling

For strict live calls:
- Missing/unsupported inspection: InspectionUnavailable; no inference.
- Inspection execution failure: InspectionFailed; no inference.
- Over-budget request: InputTokenBudgetExceeded; no inference.
- Valid request: infer once using the inspected payload.

A configuration-wide inability to initialize inspection should produce the runner's existing configuration-error outcome. A request-specific budget failure should be recorded as a technical failure for that request, not an incorrect model answer. Continue independent work only as the runner's established policy permits; preserve cancellation and global limit behavior. Count actual model calls honestly and keep existing attempt-limit semantics explicit.

Do not silently truncate input, retry without checking, invent counts, or mark a failed check as passed. Successful completion of unrelated cases must not hide technical failures in the final run summary.

## Small implementation and verification steps

After the public API and experiment-edit scope are approved:

1. Add mocked regression tests for original predict(), opaque wrappers, and stored-response replay. Establish the compatibility expectation first.
2. Implement the shared compatibility/strict split and test exact-limit, over-limit, unavailable and failed inspection. Verify zero model calls on rejection and one on success.
3. Add explicit strict selection through building blocks with mocked boundary tests.
4. Migrate a live wrapper in a small commit; verify agent reuse, config matching and payload identity.
5. Migrate Batch V2 live/replay routing only with specific approval. Verify that replay and fixtures work while real SDK/tokenizer imports are blocked.
6. Verify resume, inference sharing, output contracts, failure isolation and call accounting with existing assertions retained.
7. Sharon runs an optional small real live experiment on his machine. Report its outcome separately from unit tests; mocked tests do not establish SDK/tokenizer parity.

Do not run experiments as part of writing this document. Do not add SDK fixture bundles, vocabulary files, licenses for copied fixtures, or raw evidence logs. Summarize future checks and their exit results in PR notes or the existing verification document.

## Acceptance and merge gate

- Existing experiments keep working under the chosen compatibility contract.
- Strict live mode demonstrably checks the matching payload and fails before inference.
- Replay and fixtures require no real tokenizer and make no false budget claims.
- Batch V2 behavior outside approved inspection wiring stays unchanged.
- All pre-existing experiment edits in PR #23 are explicitly reconciled; a document alone does not resolve them.
- Public API choice, model-profile simplification and verification limitations are recorded.
- No merge is authorized by this design-document request.
