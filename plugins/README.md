# Hook Laya plugin

Connect System One Harness to Claude Code. The plugin runs the
`system-one-harness hook` command when you submit a prompt.

## Prerequisites

- macOS/Linux and a Python 3.11+ environment with pip.
- A checkout of System One Harness that includes its CLI.
- Claude Code 2.1.280+ for the plugin-directory setting shown below.
- For enrichment: the Laya/MLX runtime and model weights in your chosen Python
  environment, plus the built TypeScript helper. See the [project setup](../README.md#requirements).
  Real Laya inference currently requires Apple Silicon. The logging check below
  does not require a model or the TypeScript helper.

## 1. Install the CLI

Use the Python interpreter you want LAYA to run with. Replace the example paths
with your own; your environment can live anywhere and need not be called `.venv`.

```bash
"/path/to/environment/bin/python" -m pip install -e "/path/to/laya-context-router"
"/path/to/environment/bin/python" -m cli doctor
```

`doctor` prints the interpreter, **CLI install location**, log file location,
and basic local checks. Copy the printed CLI path and verify it runs:

```bash
"/path/to/environment/bin/system-one-harness" doctor
```

The installed command uses the interpreter selected during installation. It does
not bundle Python or install the model. `doctor` does not check model readiness,
the TypeScript helper, or whether Claude loaded the plugin.

## 2. Register the plugin

From the repository root, copy `plugins/hook-laya`, including its hidden
`.claude-plugin` directory:

```bash
mkdir -p "$HOME/.claude/sl-plugins"
cp -R plugins/hook-laya "$HOME/.claude/sl-plugins/"
```

For an existing installation, update the files inside the installed `hook-laya`
folder and preserve any intentional local configuration.

Merge these entries into `env` in `~/.claude/settings.json`. Use your actual
absolute paths, with no `~` or extra quote characters inside the values:

```json
{
  "env": {
    "LAYA_CONTEXT_ROUTER_CLI": "/path/to/environment/bin/system-one-harness",
    "CLAUDE_CODE_PLUGIN_DIRS": "/Users/example/.claude/sl-plugins/hook-laya"
  }
}
```

Preserve other settings and plugins. On macOS/Linux, separate multiple plugin
paths with `:`, for example `/path/to/hook-logger:/path/to/hook-laya`.
Alternatively, use `claude --plugin-dir /absolute/path/to/hook-laya` and keep only
the CLI variable from the example. Register this plugin once.

`LAYA_CONTEXT_ROUTER_CLI` is the retained compatibility key and points to the **installed SOH executable**, not a repository
folder or Python interpreter. It replaces `LAYA_CONTEXT_ROUTER_PROJECT_DIR` for
this hook. You may export it before launching Claude instead of using settings.
Settings environment values are available to the hook, not to your terminal.

## 3. Check logging first

The shipped hook enables enrichment with `--real`. For an initial logging check,
replace its `command` value in the installed `hook-laya/hooks/hooks.json` with:

```json
"command": "\"${LAYA_CONTEXT_ROUTER_CLI}\" hook --hook UserPromptSubmit --observe-only"
```

Exit Claude and start it again in your project. Use `/hooks` to check that
`UserPromptSubmit` is registered, then submit a short prompt. Read recent logs:

```bash
"/path/to/environment/bin/system-one-harness" logs --last 5
```

Look for `hook_observed` with `dispatcher_invoked: false` and `gateway_finished`
with `outcome: observed`. This mode records the hook input and project information,
calls no dispatcher or model, and sends no text to Claude. If other activity has
written more logs, increase `--last`.

## 4. Enable enrichment

Once the real-mode prerequisites are installed, restore the shipped command:

```json
"command": "\"${LAYA_CONTEXT_ROUTER_CLI}\" hook --hook UserPromptSubmit --repository-root \"${CLAUDE_PROJECT_DIR}\" --real"
```

Restart Claude. Claude supplies `CLAUDE_PROJECT_DIR`; do not set it yourself.
It identifies the project whose code should be read, not the Laya installation.
You do not need to edit this command when starting Claude in another project.
For worktree sessions, this variable can still point to the original checkout.
Optional gateway configuration can be passed with `--config /absolute/path/to/config.json`.

## Everyday use and troubleshooting

- **Recent logs:** `system-one-harness logs` shows the last five lines;
  `logs --last 20` shows more. Use the full CLI path if it is not on your terminal's PATH.
- **Missing executable or bad interpreter:** run the configured CLI path directly.
  Reinstall with your chosen Python if the environment was moved or removed,
  then update `LAYA_CONTEXT_ROUTER_CLI` with the path printed by `doctor`.
- **Module not found:** install the project into that same Python environment.
- **No logs:** check `/hooks`, the CLI path and Claude's hook error output.
  Run `doctor` to find the actual log file and check access. A zero exit code alone
  does not prove a log was written. Restart Claude after changing setup.
- **Python changes:** editable installation picks up source changes on the next
  hook invocation. Reinstall after entry-point or packaging changes. TypeScript
  helper source changes still require rebuilding the helper.

Use only `hook` in the hook command. `doctor` and `logs` print information intended
for a person, rather than hook responses.
