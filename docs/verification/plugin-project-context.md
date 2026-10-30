# Plugin project-context verification

Live Claude verification: **PENDING — user-run evidence required**. No plugin has been copied, installed or enabled by the implementing agent. No user's `.claude` folder or settings have been changed.

## Manual acceptance test

The user performs setup and all live steps. Follow the plugin README using your preferred plugin-loading method. Record the actual method: using `--plugin-dir` proves project identification but does not verify the preferred settings/env loading recipe.

1. Record `claude --version`, OS, LCR commit and selected Python interpreter. Use Claude v2.1.280 or later for `CLAUDE_CODE_PLUGIN_DIRS`.
2. Prepare two disposable project folders A and B. Do not hardcode/export `CLAUDE_PROJECT_DIR`; Claude must supply it.
3. For this transport test only, manually remove `--real` from your plugin command. Retain the explicit `--repository-root "${CLAUDE_PROJECT_DIR}"`. This avoids Laya inference; the feature should return `model_disabled` after successful ingestion, with empty stdout and exit 0. That is an explicit handled error, not a successful feature result.
4. Open two terminals. In A, run `cd /absolute/project-A` then `claude --debug-file /absolute/evidence/claude-A.log`. In B, run the equivalent for project B. For the preferred settings-based setup, do not add `--plugin-dir`.
5. Leave both sessions open. Submit “Reply OK” in A, then B, then A, then B. Record order and timestamps.
6. Inspect Claude diagnostics for plugin loading and the actual gateway command. Inspect LCR `logs/debug.jsonl` for `project_context_ingested` and correlated `gateway_finished` records.

For every A event, `claude_project_dir` and canonical `project_dir` must identify A; B events must identify B. Expect A/B/A/B without carryover. Session IDs distinguish sessions, invocation IDs distinguish events, and PID identifies the spawned process (OS PIDs can eventually be reused). Confirm source/status, exact event cwd, one invocation per prompt and empty protocol output in the no-real test. A missing log, import failure or plugin-load error does not count as a passing no-op.

The source boundary is still supplied explicitly by `--repository-root`. With this command and ordinary A/B projects, it should correspond to each session's project. Mocked environments and synthetic gateway inputs cannot establish this live result.

The user restores `--real` afterward and handles temporary settings changes/cleanup, preserving pre-existing entries. The agent must not perform that setup or cleanup. Share only necessary log excerpts, not full transcripts or unrelated debug data.

## Additional coverage

Deterministic tests cover A/B interleaving, missing/invalid environment, explicit source-root preservation, symlinks, Unicode/spaces, cwd independence, protected envelope fields, and timeouts. A live nested-cwd/worktree characterization is separate; do not infer a change in Claude's cwd from `cd` in another shell. No automatic worktree checkout selection is implemented.

## Results

Final full Python regression: **818 passed, 3 existing skips in 194.20 seconds** (`python3 -m pytest -q --junitxml=/tmp/lcr-project-verified.xml`). The 3 prior skips remain unchanged. Live test observations remain pending until the user supplies actual evidence. This procedure does not verify Laya classification quality or prove Claude used injected context.

## Implementation review and recovery notes

Astra approved the connector-based publication from exact current main and the use of the existing enrichment seam. The enrichment method accepts an explicit logger dependency; existing injected dispatcher/enricher callback signatures are preserved. Metadata validation requires a canonical existing directory when non-null; missing/invalid environment values remain nonfatal metadata outcomes.

During implementation a new test filename collided with the existing collector test. The original `tests/test_project_context.py` was restored byte-for-byte (blob `a40eefeaf927b55e747106626ffff93f228b9ac0`), and the new tests live in `tests/test_hook_project_context.py`. Earlier overlapping/interrupted full-suite runs are invalid evidence and are excluded. All task-started duplicate runs were stopped through their original execution sessions before the final run.

Focused final verification: **155 passed**, including the restored collector tests, new project-metadata tests, common and event dispatch, and gateway transport. The single clean final run passed: **818 passed, 3 existing skips**. No TypeScript source or invocation algorithm changed.
