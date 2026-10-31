# Observe-only hook mode

## Approved scope and review

Sharon's latest request, 31 October 2026: connect the plugin manually and inspect the
raw event and derived project metadata before enabling any dispatcher or Laya work.
The approved flag is `--observe-only`, mutually exclusive with `--real`.

This scope supersedes the separate dispatcher-experiment/live-suite plan for this
change. It does not implement that older plan's real-model experiment or live suite.
A separate review agent confirmed this interpretation and supplied the additional
failure-path tests below. No plugin activation or user configuration edits are part
of implementation.

## Behavior

The gateway keeps its existing argument validation, 65,536-character stdin limit,
deadline, stdout isolation and fail-open exit convention. Observation branches
before common/event dispatch. It never invokes an injected dispatcher, the normal
dispatcher, an event handler, Laya, the TypeScript helper, or source extraction.
It does not load `--config` or read `--repository-root` source content.

Records use the existing JSONL sink and existing PID, parent PID and invocation ID
metadata:

- `observation_input_received`: original bounded stdin text as read by the gateway,
  read count, limit, and truncation flag. It precedes JSON validation, preserving
  available evidence for malformed JSON, duplicate keys, mismatch and oversized
  input. For oversized input the captured prefix is limited to 65,536 characters;
  the existing extra-character probe detects overflow. This is a text capture,
  not a byte-for-byte capture of the underlying pipe encoding.
- `hook_observed`: parsed original payload including unknown fields, the raw
  `CLAUDE_PROJECT_DIR`, canonical `derived.project_dir` or null, resolution status,
  process cwd, payload cwd, source-root argument and intended dispatch destinations.
  Project validation reuses normal mode's canonical-directory resolver. A missing
  or invalid project value is recorded rather than guessed from cwd.
- `dispatcher_invoked` is false. `would_invoke_dispatcher` names the common gateway
  destination; `event_dispatcher` names the supported event destination or is null
  for an unsupported hook. This metadata reports the route without importing or
  running dispatchers.
- `gateway_finished`: outcome `observed`, reason `observe_only`, no response and
  zero stdout bytes after successful primary observation logging. Rejected input
  remains outcome `error`, with its existing error code. Logging failure produces
  stderr diagnostics and an error outcome when the remaining sink is writable;
  it does not claim a successful observation.

Only the named project environment variable is recorded; the full environment is
not dumped. No project source or transcript is opened. Resolving the project
directory checks filesystem metadata and symlinks.

Every observation invocation finishes with empty stdout and exit 0, including
handled failures. Diagnostics are stderr/file only. The observation path does not
print a normal `noop` diagnostic. A timeout may prevent final logging; stderr then
contains the deadline diagnostic and success must not be inferred from exit 0.

## Verification plan

1. Supported event: original whitespace/Unicode and unknown nested fields survive;
   derived paths remain separate; exact stdout is empty.
2. Same-process A/B/A/B runs: project/session values and invocation IDs do not leak.
3. Missing, empty, relative, nonexistent, file and symlink project values have the
   same statuses as normal enrichment.
4. Dispatch spy and import guards prohibit dispatch, model and source boundaries;
   absent config/source root/helper/runtime do not block observation.
5. Unsupported hook records no event route; mismatched event is rejected.
6. Conflicting modes, bad arguments, malformed JSON, duplicate keys, non-object
   JSON, missing event name and oversized input keep safe output/error behavior.
7. Noisy, failing and deadline-interrupted loggers cannot contaminate stdout or
   falsely pass observation.
8. Default log sink format includes complete evidence and process correlation.
9. Existing gateway, deadline, dispatch and project-context regressions continue
   to pass. No real model or installed Claude session is run in automated tests.

## Manual first test

See [the plugin setup](../plugins/hook-laya/README.md#observe-only-first-test).
Sharon supplies the interpreter and manually loads the plugin. First run Project A,
then B, and compare the actual received environment and payload with expectations.
This live Claude test remains pending; synthetic subprocess tests only establish
the gateway's handling of inputs supplied by the test.

## Implementation verification — 31 October 2026

Base: `6ff26007c1455179e6f84c88f41a0b23ac32146b`. Verification ran in an isolated
Python 3.12 environment with pytest 9.2.0 and a locally built TypeScript helper.
No Laya runtime/model was installed or called; no Claude session was launched.

- New observation suite: 24 passed. It includes subprocess output/import guards,
  same-process A/B/A/B, default sink success/failure and both primary-write failures.
- Focused observation/gateway/project/deadline/audit regressions: 117 passed.
- Full existing Python suite excluding the new file: 817 passed, 3 skipped, and one
  environment-only packaging failure (missing pip/setuptools/wheel in the uv-created
  virtual environment). The review agent diagnosed this and instructed installation
  of those build tools into the isolated environment. The unchanged packaging test
  plus all 24 observation cases then passed: 25 passed. Thus all 842 executed unique
  Python tests passed across these verification runs; no implementation failure
  remains. The full suite was not needlessly repeated after adding build tools.
- The three existing skips are one concurrent outside-project symlink replacement
  scenario and two legacy configuration duplicate-key cases, already deferred for V1.
- TypeScript helper: build succeeded; all 122 tests passed.
- `git diff --check`: passed.

Commands:

```bash
.venv/bin/python -m pytest -q tests/test_hook_observe_only.py tests/test_hook_project_context.py tests/test_hook_gateway_transport.py tests/test_hook_deadline_lifecycle.py tests/test_hook_gateway_audit.py
.venv/bin/python -m pytest -q --ignore=tests/test_hook_observe_only.py
.venv/bin/python -m pytest -q -rs tests/test_packaged_blocks.py tests/test_hook_observe_only.py
npm --prefix typescript-helper run build
npm --prefix typescript-helper test
```

During implementation, two generated test scripts initially used a placeholder
that also replaced the suffix of `LOG_PATH`, causing a syntax error before the
gateway ran. Per Sharon's instruction, the separate review agent corrected the
fixtures and verified the 24-case suite; the broader 117-case rerun passed. Neither
this correction nor the packaging environment fix changed production semantics.

The same reviewer checked the implementation and manual docs against the approved
scope and found no production blocker. Actual installed-plugin A/B behavior and
Claude payload delivery remain user-run verification tasks.
