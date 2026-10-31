# Laya Context Router CLI: plan and usage

## Goal and scope

Expose one command, `laya-context-router`, installed using the user's chosen
Python interpreter. Each machine may use a different interpreter or environment.
The public command names and arguments stay the same.

This change is additive. No existing Python method, gateway, dispatcher, feature,
model adapter, logger, log location, hook configuration or experiment is changed.
The only edited existing file is `pyproject.toml`, to register the console command.
The old `python -m laya_context_router.hooks.gateway` invocation remains supported.

## Files

- `src/laya_context_router/cli/__init__.py`: command selection and gateway delegation.
- `src/laya_context_router/cli/__main__.py`: `python -m laya_context_router.cli` support.
- `src/laya_context_router/cli/doctor.py`: read-only installation diagnostics.
- `src/laya_context_router/cli/logs.py`: read the existing log's last N lines.
- `pyproject.toml`: `[project.scripts]` registration pointing to `cli:main`.
- `tests/test_cli.py`: focused compatibility and actual installed-command tests.
- This document: installation, migration, boundaries, tests and rollback.

## Commands and contracts

### hook

```bash
laya-context-router hook --hook UserPromptSubmit --observe-only
```

Remove only the leading `hook` token and call the existing `gateway.main(argv)`.
Do not read stdin, change cwd/environment, rewrite flags, print a banner, run
preflight checks, catch gateway errors or reinterpret its return value. Gateway
validation, help behavior, deadlines, raw-input bounds, logging, stdout protocol
and fail-open exit convention remain its responsibility. Future gateway options
pass through without changing the CLI. Configuration errors before reaching the
`hook` subcommand are normal CLI usage errors (exit 2).

The gateway's existing timer implementation targets Unix (including macOS).
This adapter does not add Windows support.

### doctor

```bash
laya-context-router doctor
```

Report the actual interpreter, Python version, package directory, standard
installation location of the CLI, and the existing logger's exact file path.
Check Python >= 3.11, gateway timer availability, and estimated log write access.
Inspect filesystem metadata only; do not create logs/directories or import models.
Print human-readable diagnostics on stdout; return 0 if these basic checks pass,
otherwise 1. A write-access estimate is not proof of a successful log append.

This first version explicitly reports Laya/MLX, model weights, Node/TypeScript
helper and Claude plugin loading as NOT CHECKED. Model setup is deferred.
`doctor` must never imply the complete real-inference flow is ready.

### logs

```bash
laya-context-router logs
laya-context-router logs --last 5
```

Default to five lines from the existing `log_utils.LOG_PATH`. Preserve original
JSONL text, including Unicode; read sequentially and keep only the last N lines
in memory. N must be a positive integer. This is an on-demand tail, not a watcher;
it scans the existing file and may be slow for very large logs.

Missing file: print its path and an explanatory message on stderr, return 0,
create nothing. Empty file: return 0 with no output. Other file/decoding errors:
stderr explanation, return 1. No rewriting, truncation, rotation or filtering.
Logs can contain raw prompts; this command prints existing content as requested.

## Install with your chosen Python

From the LCR repository directory, replace the example interpreter path with the
one that already works for you. It need not be inside the repository:

```bash
"/absolute/path/to/chosen/python" -m pip install -e .
"/absolute/path/to/chosen/python" -m laya_context_router.cli doctor
```

The package installer generates the `laya-context-router` console launcher in
that interpreter environment's scripts directory. `doctor` prints the standard
location. This guide assumes a normal environment installation, not `--user`,
`--target` or `--prefix`. Verify that the printed launcher exists and run:

```bash
"/absolute/path/to/environment/bin/laya-context-router" doctor
"/absolute/path/to/environment/bin/laya-context-router" logs --last 5
```

The short command works when that scripts directory is on PATH. Claude's hook
should use the verified absolute launcher path so it does not depend on shell
activation or PATH. No new `.venv` naming convention or Python environment is
created by this change. The generated launcher is tied to the chosen interpreter;
this is an installed CLI, not a bundle containing Python or MLX.

## Manual plugin migration

After installation succeeds, change only the command in your installed copy of
`hooks/hooks.json`. Example logging-only entry (replace the launcher path):

```json
"command": "\"/absolute/path/to/environment/bin/laya-context-router\" hook --hook UserPromptSubmit --observe-only"
```

For real mode, preserve all existing gateway options, including the source root:

```json
"command": "\"/absolute/path/to/environment/bin/laya-context-router\" hook --hook UserPromptSubmit --repository-root \"${CLAUDE_PROJECT_DIR}\" --real"
```

No plugin files or user settings are modified by installation or this PR. Restart
Claude after changing its installed hook command, submit a normal prompt and
inspect `logs --last 5`. Test Projects A and B separately. Observation must log
`dispatcher_invoked: false` and `outcome: observed`, with zero stdout bytes.
Do not use `doctor` or `logs` as the hook command: they produce human-facing output.
The direct-launcher examples no longer use `LAYA_CONTEXT_ROUTER_PROJECT_DIR`.

## Daily development and rollback

Editable installation follows Python source changes on the next hook invocation.
Reinstall after entry-point/installation metadata changes, and update dependencies
when required. TypeScript source changes still require their existing build.
Moving/removing the selected environment or editable repository may require
reinstallation and updating the absolute launcher path.

Rollback is limited to restoring the previous hook command. Existing gateway
entry points and methods are retained. Installing this package does not install
Laya/MLX, fetch model weights or build/package the TypeScript helper; those remain
separate prerequisites for real mode.

## Focused verification plan

1. A forwarding spy receives identical arguments and the same stdin object; the
   CLI propagates its return code and emits no additional stdout/stderr.
2. Subprocess comparison with the old gateway proves identical response stdout
   and exit status for context, no-op, failure, malformed JSON and observe-only.
3. Recent-log output preserves line order/content; missing and unreadable paths
   are handled without writing. Invalid CLI arguments return usage errors.
4. Doctor identifies the interpreter/log path, performs no writes and reports a
   blocked log destination as failure without claiming model readiness.
5. Build a wheel and install it into a fresh environment whose path contains
   spaces. Launch the generated executable from outside the repository, with no
   PYTHONPATH. Verify doctor, observe-only and reading the resulting log. This
   proves real packaging and interpreter selection without Laya/MLX installed.
6. Run existing gateway transport and observe-only tests. Verify no existing
   methods differ from the main-branch baseline.

## Completion evidence

Recorded after running the focused checks; installed Claude testing on Sharon's
Mac remains a separate manual step.

Implementation completed on 31 October 2026 against main commit
`ce6bd62b08152779c27ce72b13421612845c332c`.

- New CLI suite: 15 passed, including installation into a fresh environment with
  spaces in its path and execution outside the checkout without PYTHONPATH.
- Existing gateway transport and observation suites: 73 passed.
- All 35 pre-existing Python source files match the remote baseline byte for byte.
- No model runtime was installed or invoked by these checks.
- No user plugin/settings files were edited and no installed Claude session was run.

Commands used:

```bash
python -m pytest -q tests/test_cli.py
python -m pytest -q tests/test_hook_gateway_transport.py tests/test_hook_observe_only.py
```
