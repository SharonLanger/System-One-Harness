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
            "command": "\"/absolute/laya-context-router/.venv/bin/python\" \"/absolute/laya-context-router/hooks/user_prompt_submit.py\" --repository-root \"$CLAUDE_PROJECT_DIR\" --config \"/absolute/run-config.json\" --real --deadline 10",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
```

Replace the interpreter path with the absolute Python executable that has this
package and the supported backend installed. Use a synchronous `command` hook;
do not set `async: true`. Inspect registration with Claude Code's `/hooks` in
the disposable project. To disable it, remove this UserPromptSubmit entry; keep unrelated hooks. Omitting
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
context budgets refuse oversized data without truncating it. The 8,000-character
default applies to the entire rendered string (including code, labels and
provenance), below the documented 10,000-character overflow behavior. It is
separate from the Laya input budget. Ordinary Python output and synchronous
native writes to fd 1 during model work are redirected to stderr; actual SDK
background output behavior still needs a supported-environment check.

Synthetic input for the currently supported narrow flow (not a captured run):

```json
{"session_id":"example","cwd":"/repo","hook_event_name":"UserPromptSubmit","prompt":"Explain `src/service.ts`: how does calculate work?"}
```

The adapter emits one JSON line shaped like this after a successful selection;
the source and metadata shown here are illustrative, not a runtime trace:

```json
{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"Selected TypeScript context (partial):\n{\"path\":\"/repo/src/service.ts\",\"code\":\"function calculate(x: number) { return x * 2; }\",\"coverage\":\"partial\"}"}}
```

The real context also includes the extractor's actual source hash, callable
identity, line ranges, import/dependency information and numbered display code.
This `additionalContext` accompanies the original prompt; it does not replace it.
The input key `hook_event_name` and output key `hookEventName` have different
spellings. A top-level `additionalContext` is incorrectly nested and can be
ignored by Claude Code even though its JSON parses. Ineligible, ambiguous,
oversized and handled failure cases emit **no stdout and exit 0**, with a reason
on stderr. A successful subprocess response establishes protocol output only;
actual delivery to Claude and actual Laya inference have separate final checks.

These contracts are
checked against the unversioned official [hooks reference](https://code.claude.com/docs/en/hooks),
retrieved 29 October 2026. No actual Claude version or delivery is claimed.
