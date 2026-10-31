# Hook Laya plugin

Claude Code calls the installed Laya gateway whenever you submit a prompt.

## Where the two paths come from

| Value | Who supplies it? | Purpose |
| --- | --- | --- |
| `LAYA_PYTHON` | You set it once in Claude settings. | Python interpreter where Laya Context Router is installed. |
| `CLAUDE_PROJECT_DIR` | Claude Code supplies it automatically for each session. | The project whose code Laya should read. |

For example, start Claude in `/Users/sharon/work/project-A`. Claude supplies that
folder as `CLAUDE_PROJECT_DIR`. The hook expands `--repository-root "${CLAUDE_PROJECT_DIR}"`
to `--repository-root "/Users/sharon/work/project-A"`. Start another session in
Project B and the same hook receives Project B's folder. You do not edit the hook
between projects or put `CLAUDE_PROJECT_DIR` in your settings.

`--repository-root` tells the enrichment flow where to resolve source files. It is
the target project's root, not the Laya installation or plugin directory. The
current real-mode flow requires this argument; removing it disables enrichment
with an `invalid_project_root` error. Observation does not need it.

## Prerequisites and setup

1. Use Python 3.11+ with this repository installed. For an existing virtual
   environment, run the following with your actual installation paths:

   ```bash
   "/Users/example/dev/laya-context-router/.venv/bin/python" -m pip install -e "/Users/example/dev/laya-context-router"
   ```

   Real inference additionally needs the [main README's](../../README.md) Laya/MLX,
   model weights and TypeScript helper setup. Observation needs none of those.

2. Copy this complete plugin folder, including `.claude-plugin`, to
   `~/.claude/my-plugins/hook-laya`.

3. Merge these entries into `env` in `~/.claude/settings.json`. Replace the example
   paths with your own full absolute paths; do not use `~` in the JSON values:

   ```json
   {
     "env": {
       "LAYA_PYTHON": "/Users/example/dev/laya-context-router/.venv/bin/python",
       "CLAUDE_CODE_PLUGIN_DIRS": "/Users/example/.claude/my-plugins/hook-laya"
     }
   }
   ```

   Preserve existing settings and plugin paths; separate plugin paths with `:` on
   macOS/Linux. `CLAUDE_CODE_PLUGIN_DIRS` requires Claude Code v2.1.280 or later.
   Alternatively, load the folder using `claude --plugin-dir /path/to/hook-laya`
   and set only `LAYA_PYTHON` in settings. Use one registration method, and remove
   any duplicate old hook registration. Start a fresh Claude session.

The interpreter path now lives in settings, not in `hooks/hooks.json`. These
instructions target macOS/Linux shell commands. Settings environment values apply
to Claude's child processes; they do not export variables into your terminal.

## Observe-only first test

In the copied plugin's `hooks/hooks.json`, replace the `command` value with:

```json
"command": "\"${LAYA_PYTHON}\" -m laya_context_router.hooks.gateway --hook UserPromptSubmit --observe-only"
```

There is no repository-root argument for this test. Claude still supplies the
project environment and hook JSON automatically. The gateway logs them without
calling any dispatcher, model or source-reading feature, and sends zero stdout
bytes to Claude (no enrichment and no no-op text).

Start a fresh session in Project A and submit a prompt, then repeat in Project B.
In an editable installation, inspect `<laya-context-router>/src/logs/debug.jsonl`:

- `observation_input_received`: original stdin text, bounded to 65,536 characters.
- `hook_observed`: raw payload, `claude_project_dir`, `derived.project_dir`,
  `payload_cwd`, `process_cwd`, intended dispatcher and `dispatcher_invoked: false`.
- `gateway_finished`: `outcome: observed` and `stdout_bytes_written: 0`.

Compare project paths and session IDs. Exit 0 alone does not prove successful
logging; check stderr and the records. See the [test plan](../../docs/observe-only-plan.md).

## Enable enrichment after the test

Restore the command shipped in this repository:

```json
"command": "\"${LAYA_PYTHON}\" -m laya_context_router.hooks.gateway --hook UserPromptSubmit --repository-root \"${CLAUDE_PROJECT_DIR}\" --real"
```

`--hook` identifies the event; `--real` enables Laya. Claude provides the project
path and the shell passes it to the gateway. Nothing needs a per-project edit.
Optional model configuration can be supplied using `--config /path/to/config.json`.

## Troubleshooting and limitations

- Command not found: check that `LAYA_PYTHON` names an existing executable. It must
  be the interpreter path only, without extra arguments or embedded quote characters.
- Module not found: install this repository into that exact interpreter (step 1).
- No hook logs: verify plugin loading and restart Claude after configuration changes.
- Missing project environment: observation records it; real enrichment cannot use
  an empty source root. Do not assume that a manually launched terminal command
  has Claude's environment.
- Worktrees: Claude's project variable can remain at the original checkout while
  the payload's `cwd` changes. This command reads the original project; it does not
  automatically switch source roots to a worktree.

Installed-plugin A/B verification remains a manual test; subprocess tests do not
prove what your Claude installation sends. See [A/B verification](../../docs/verification/plugin-project-context.md).

References: [Claude hook environment](https://code.claude.com/docs/en/hooks#reference-scripts-by-path),
[environment settings](https://code.claude.com/docs/en/env-vars).
