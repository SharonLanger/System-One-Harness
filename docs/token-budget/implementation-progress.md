# Token-budget implementation status

The branch contains implementation through increment 10. Latest published implementation commit before this cleanup: `9600df2a0684a63df280f0052314defdf5f115f0`. Increment 11 was prepared but remained unpublished; it has been preserved separately and removed from this worktree. No PR merge or main integration is included.

## User-directed mock-only cleanup

The latest instruction explicitly replaces real-tokenizer unit tests with mocked boundaries and removes the fixture bundle. This overrides the historical plan's mandatory real-fixture/parity requirements.

Changes:

- Removed `tests/fixtures/token-budget/` in full, including copied SDK code, tokenizer/model configuration, manifest and associated licenses/notices.
- Removed the preparation script and obsolete prepared-fixture ignore rule; test dependencies now require pytest only.
- Replaced real encoding/SDK parity tests with controlled token IDs, rendered-input assertions and hand-specified sequence/marker expectations. Preserved accounting boundaries, all-question rejection, snapshots, error/log correlation, mutation detection and block propagation tests.
- Removed tracked raw execution output under `docs/token-budget/evidence/`; preserved it outside the checkout and in existing Git history.
- Production loaded-tokenizer behavior is unchanged. `ExactTokenizer` remains because production verification uses it. No experiment files were edited or experiment tests/run commands executed for this cleanup.

Coverage limitation: current unit tests do not establish real-tokenizer or SDK parity. Historical measurements are not a current qualification claim. Experiment cleanup and runtime/hash simplification remain pending.

Validation: mocked budget suite passed 128 tests. Repeated with imports of tokenizers, numpy and laya_mlx actively blocked: 128 passed in 1.13s, and none of those modules were loaded. Selected non-experiment prediction/configuration/question/interpretation/block regressions passed 270 tests in 3.02s. No full-suite or experiment run was performed for this cleanup. Git diff checks passed; production executable AST is unchanged. Prior experiment edits already present in the PR remain pending cleanup; this commit makes no additional experiment changes.

## Authorized compatibility completion

The follow-plan instruction selects legacy `predict` plus explicit `predict_strict`. Both share response validation/copying; only strict calls inspect and reject. `strict=True` is explicitly forwarded by QuestionBlock, Block.run, public question blocks and the sandbox flow. Default callers/replay remain unchecked and emit no fitting report. Opaque strict calls refuse. New compatibility tests were red (5 failures); split and block tests passed 68 checks. Existing signature assertions were updated only for the intentional additive strict keyword. Next: documented static profiles, exact latest-main experiment restoration, and final regression.
