# Isolated hook protocol and future project-local use

Run this offline scenario after building the TypeScript helper:

```bash
PYTHONPATH=src python examples/user_prompt_submit_scenario.py
```

It creates a disposable source repository and launches the actual hook through
Bash/Python. Only `laya_mlx.load`/the returned agent are simulated, using a fixed
request/response checked at that boundary. The real adapter, question construction,
validation, enrichment, rules, flow, parser and extraction execute. It emits the
hook protocol object and labels the SDK simulation on stderr. No Claude command,
real SDK, model load or settings write occurs. This proves protocol mechanics;
actual Claude delivery and model selection quality remain unverified.

The following is a **future manual recipe**, after Phase 20 verifies a supported
Laya environment, checkpoint/settings and isolated Claude delivery. It has not
been activated here. Install the Python package in the interpreter used by the
command, build the pinned helper in its source checkout, replace the two absolute
placeholder paths and supply verified RunConfig JSON. The repository root comes
from Claude's project directory, while event cwd can be nested beneath it.

Merge this entry into project-local `.claude/settings.local.json` only when
activation is authorized for that project; preserve unrelated settings:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"/absolute/laya-context-router/hooks/user_prompt_submit.py\" --repository-root \"$CLAUDE_PROJECT_DIR\" --config \"/absolute/run-config.json\" --real --deadline 10",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
```

To disable it, remove this UserPromptSubmit entry; keep unrelated hooks. Omitting
`--real` also makes this adapter return a safe no-op without importing the SDK.
Removing an entry changes configuration, and actual Claude reload/disable behavior
must be checked in the supported final environment. Tests parse the recipe, run
its command with the child-only SDK fake, and verify the opt-out command, without
creating a `.claude` directory or configuring Claude.

`--deadline` defaults to 10 seconds; a finite explicit value up to 300 seconds is
an administrative limit. The outer hook `timeout` must exceed that configured
value with grace (the example adds 5 seconds). Cold loading and inference happen
in each new process and are unmeasured. POSIX signals cannot guarantee immediate
interruption of native SDK computation. Adjust only after measuring the supported
real setup; the current default Claude UserPromptSubmit timeout is 30 seconds.

Accepted context is one `hookSpecificOutput` object containing `hookEventName`
and string `additionalContext`. The original prompt is preserved. Safe no-ops
and handled errors exit 0 with empty stdout; diagnostics go to stderr. Source
context is partial, not a complete explanation or dependency graph. Input and
context budgets refuse oversized data without truncating it. These contracts are
checked against the unversioned official [hooks reference](https://code.claude.com/docs/en/hooks),
retrieved 29 October 2026. No actual Claude version or delivery is claimed.
