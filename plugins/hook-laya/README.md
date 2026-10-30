# Hook Laya plugin

The supplied manifest and `hooks/hooks.json` register `UserPromptSubmit`.
The command calls `scripts/hook.py UserPromptSubmit`, which forwards the event
name and arguments to `laya_context_router.hooks.gateway.main`. Stdin and stdout
pass through unchanged; the launcher does not parse the event or emit context.

## Load from this checkout

First complete the repository's Python/Laya environment and TypeScript helper
setup from the main README. Activate that Python environment before starting
Claude: the hook uses `python` from its inherited PATH, and that interpreter must
have this repository installed (`python -m pip install -e /absolute/path/to/laya-context-router`).

Start Claude in the project whose TypeScript files you want to explain:

```bash
cd /absolute/path/to/target-project
claude --plugin-dir /absolute/path/to/laya-context-router/plugins/hook-laya
```

This loads the plugin for that session. No marketplace or global registration is
required. Do not register the outer compatibility hook separately for the same
event, or the flow will run twice.

Claude supplies `CLAUDE_PLUGIN_ROOT` for locating the launcher and
`CLAUDE_PROJECT_DIR` for the explicitly configured `--repository-root`.
The command enables the existing model flow with `--real`. To use a run
configuration, append `--config "/absolute/path/to/run-config.json"` to the
command in `hooks/hooks.json`. Other gateway options can be appended there too.

Additional events can use the same launcher with their exact Claude event name
as its first argument. Only UserPromptSubmit has a feature dispatcher today;
unsupported events return empty stdout without model work.

References: [Claude plugin loading](https://code.claude.com/docs/en/plugins)
and [hook reference](https://code.claude.com/docs/en/hooks).
