# Hook Laya plugin

This folder contains configuration only. Claude launches the installed Laya Context Router gateway directly; no plugin launcher script is needed.

## Set up manually

Each user chooses how to load the plugin. The repository does not copy files, install or activate plugins, edit settings, or provide an installer script. The following is Sharon's preferred setup; other supported plugin-loading methods work too.

There are four different paths:

- LCR repository: `/Users/example/dev/laya-context-router`.
- Python interpreter with Laya/MLX: `/Users/example/dev/laya-context-router/.venv/bin/python`.
- Optional copied plugin: `/Users/example/.claude/my-plugins/hook-laya`.
- Target project: `/Users/example/work/project-A`, whose code the session discusses.

Complete the main README's Python/Laya and TypeScript helper prerequisites. Install this repository into your chosen Python environment, for example:

```bash
/Users/example/dev/laya-context-router/.venv/bin/python -m pip install -e /Users/example/dev/laya-context-router
```

This does not install Laya/MLX or model weights. The editable installation lets `python -m laya_context_router.hooks.gateway` find our repository independently of the hook's working directory. Do not run `gateway.py` directly by file path.

If you want Sharon's layout, manually copy this complete folder, including `.claude-plugin`, to `~/.claude/my-plugins/hook-laya`. In the copy's `hooks/hooks.json`, replace `/absolute/path/to/laya-python` with your interpreter's absolute path. Keep its quotes for paths containing spaces. The command runs:

```bash
"/absolute/path/to/laya-python" -m laya_context_router.hooks.gateway --hook UserPromptSubmit --repository-root "${CLAUDE_PROJECT_DIR}" --real
```

`--hook UserPromptSubmit` identifies the event and must match the stdin JSON. `--real` enables actual local Laya calls. Optionally append `--config "/absolute/path/to/run-config.json"` and existing gateway budget options.

Manually merge this property into the existing `env` object in `~/.claude/settings.json`, preserving all other settings:

```json
{
  "env": {
    "CLAUDE_CODE_PLUGIN_DIRS": "/Users/example/.claude/my-plugins/hook-laya"
  }
}
```

If other plugin paths are present, preserve them and append this absolute path with `:` on macOS/Linux or `;` on Windows. Do not use a newline or add duplicates. This environment variable requires Claude Code v2.1.280 or later. Start a fresh Claude session after configuring it.

Alternatively, configure the interpreter in your chosen plugin directory and load it with `claude --plugin-dir /absolute/path/to/plugin-folder`. The plugin does not require a particular copy destination. Do not register both methods or the old outer hook for the same event.

## What runs and how the project is identified

Each Claude CLI launches a separate local Python process for each hook event. It supplies event JSON on stdin and `CLAUDE_PROJECT_DIR` in that process's environment. Sessions in projects A and B therefore call the same LCR code with different environment values.

The gateway reads `os.environ.get("CLAUDE_PROJECT_DIR")` during the invocation. The common dispatch enrichment method adds `envelope.derived.project_dir` (canonical absolute directory, or null if missing/invalid). Original JSON, `cwd`, session ID and transcript path are preserved. The `project_context_ingested` log records the selected raw environment value, canonical directory, status, source, cwd and session; gateway logging adds invocation ID and the logger records PID. See the main README for the repository log location.

Missing/invalid project environment is metadata only and does not replace a valid explicit `--repository-root`. Source resolution continues to use that explicit argument. In this plugin command Claude's project environment supplies it; manual callers can configure another source root.

Worktree limitation: `CLAUDE_PROJECT_DIR` identifies the originating project and may stay at the original checkout while JSON `cwd` moves to a worktree. This plugin does not automatically select that other checkout; default source reads can therefore use the original checkout. Keep project identity, event cwd and source root distinct.

See [manual A/B verification](../../docs/verification/plugin-project-context.md). Automated tests do not prove that your installed Claude supplies the environment. No live verification is claimed yet.

References: [hook paths/environment](https://code.claude.com/docs/en/hooks#reference-scripts-by-path), [plugin environment variable](https://code.claude.com/docs/en/env-vars), [user-settings support](https://code.claude.com/docs/en/plugins/mods/reference#settings-and-environment-variables).
