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
context is partial, not a complete explanation or dependency graph. Input
budgets still refuse oversized input. `--max-context-chars` is now a warning
threshold, defaulting to 8,000 characters of the formatted `additionalContext`
string. Exceeding it logs `WARNING` / `context_size_warning` and sends the whole
string unchanged. It does not truncate or reject the response. This is separate
from Laya input and dependency-source budgets, which remain enforced.
`--max-dependency-depth` defaults to2 (0–20); `--max-dependency-chars` defaults
to12,000 (1–1,000,000 UTF16 code units in complete dependency source). Collection
can omit complete units only with explicit gaps. Selected code stays complete.
The final character count includes the readable method, supporting code, paths,
line ranges and notes. Raw extractor metadata stays in logs.
Ordinary Python output and synchronous
native writes to fd 1 during model work are redirected to stderr; actual SDK
background output behavior still needs a supported-environment check.

After accepted signature-based selection, project collection uses the nearest
confined tsconfig for Classic/Node10 relative imports, path mappings and proven
reexport routes. Missing, malformed or unsupported configuration retains complete
selected/local context with an explicit gap. Foreign units carry their own source
hashes/ranges; callers, runtime state, module effects and unproven dispatch remain
partial. Project source is parsed and never executed.

Synthetic input for the currently supported narrow flow (not a captured run):

```json
{"session_id":"example","cwd":"/repo","hook_event_name":"UserPromptSubmit","prompt":"Explain `src/service.ts`: how does calculate work?"}
```

The adapter emits one JSON line shaped like this after a successful selection;
the source and metadata shown here are illustrative, not a runtime trace:

```json
{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"Selected TypeScript context (partial).\n\nSelected method\n\nsrc/service.ts (lines 1–1)\nfunction calculate(x: number) { return x * 2; }"}}
```

The exact presentation is defined by `src/laya_context_router/context_format.py`.
It shows the selected source once and requested supporting declarations with
file locations. Hashes, internal IDs, UTF-16 offsets, configuration details,
duplicate display code and generic extractor limitations are omitted from the
model-facing text. The original validated extraction object remains intact in
`extractor.context_validated` logs.
This `additionalContext` accompanies the original prompt; it does not replace it.
The input key `hook_event_name` and output key `hookEventName` have different
spellings. A top-level `additionalContext` is incorrectly nested and can be
ignored by Claude Code even though its JSON parses. Ineligible, ambiguous,
input-budget and handled failure cases emit **no stdout and exit 0**, with a reason
on stderr. A successful subprocess response establishes protocol output only;
actual delivery to Claude and actual Laya inference have separate final checks.

These contracts are
checked against the unversioned official [hooks reference](https://code.claude.com/docs/en/hooks),
retrieved 29 October 2026. No actual Claude version or delivery is claimed.

## Formatter contract

`format_context(extracted_context, *, include_imports=True,
include_dependencies=True, include_notes=True, project_root=...)` returns a string and does not
mutate the validated extraction result or read additional files. The selected
method is always included in full. Import declarations and other supporting
declarations can be enabled independently. Supporting declarations are not
necessarily called methods: they may also be interfaces, constants, or types.
Notes summarize missing-context categories rather than emitting every raw gap.

Labels and source are plain text: no added Markdown headings, fences or bullets.
Original source keeps its own backticks and Markdown. Display paths are relative
to the required absolute project_root; the hook passes its validated
--repository-root. Event cwd controls file lookup, not displayed paths. The pure
formatter checks the absolute-path form; the hook validates existence and directory
containment. Raw extraction paths stay absolute.
See [the future navigation plan](call-navigation-plan.md) for the separate
outgoing/incoming helpers; neither is wired into a flow.

Paths and line ranges accompany the code so a later presentation mode can show
dependency locations instead of bodies. This formatter does not yet implement
that mode or discover extra callees; the existing call-navigation operation is
the source for any future list of called methods.

Durable formatter and hook tests cover plain presentation, exact source retention,
project-root display paths and warning-only output thresholds.


## Shared gateway entry and compatibility

New registrations should call `python -m laya_context_router.hooks.gateway --hook UserPromptSubmit` with the existing operational arguments (`--repository-root`, optional `--config`, explicit `--real`, deadlines and budgets). The earlier script path is now a forwarding wrapper; the legacy recipe above remains usable. This document does not install or activate a hook. Final plugin registration and installation preference remain pending supplied assets.

The gateway requires session_id, transcript_path, cwd, hook_event_name and prompt for UserPromptSubmit. permission_mode is optional. Transcript text is not read. Fields follow the pinned official Anthropic SDK contract documented in the field ledger; installed CLI delivery remains unverified. Unknown event names return unsupported_event without feature requirements.

The gateway resolves file references from configured project root through the reviewed opt-in root mode. Changing event/process cwd, including an unrelated directory, does not change root selection or display paths. Legacy direct flow/resolver callers retain default behavior. Source traversal, symlink and repository-prefix escapes still fail containment. This intentionally replaces the old launcher's outside-cwd rejection; malformed/relative cwd and invalid explicit root remain errors.

Replay output comes from captured stdout. Gateway logs contain metadata, not full response content. A prepared-byte count does not prove emission; an incomplete/failed write may have delivered partial bytes. Final output-write metadata and parsed stdout are separate evidence, and neither is a Claude acknowledgement.
