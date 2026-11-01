# Understand and connect the prompt hook

## First: prove the connection

Run `python experiments/hook_prompt_probe.py`, or press Play in your editor.
This uses the synthetic `replay_event` from `inputs/hook_prompt_probe.json`,
prints a readable summary and the exact hook response JSON, and saves both under
`experiments/results/hook_prompt_probe/YYYY-MM-DD_HH-MM-SS/`.
It does not call Laya or require the TypeScript build. This is a connection
probe, not the real method-selection flow and not a model accuracy test.

Edit `additional_context` in that input file to change what Claude receives.
Edit `replay_event.prompt` to change the synthetic prompt. In live mode,
`replay_event` is ignored: Claude supplies the actual event through stdin.

Every invocation logs `component: hook_prompt_probe`, `event: invoked` before
argument parsing, config loading or stdin reading. Later entries record the
received event, the context being emitted, or an error. They use the existing
`logs/debug.jsonl` file; correlate entries by PID. Reports include the PID and
log location. Reports and logs can contain your prompts and are Git-ignored.

## Connect it on your Mac

In the project where you run Claude Code, merge this entry into
`.claude/settings.local.json`, preserving any existing settings and hooks.
Replace `/ABSOLUTE/PATH/laya-context-router` with your checkout's path and use
the Python interpreter you already use for experiments. No settings are
installed automatically by this experiment.

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"/ABSOLUTE/PATH/laya-context-router/.venv/bin/python\" \"/ABSOLUTE/PATH/laya-context-router/experiments/hook_prompt_probe.py\" --hook",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

Start a fresh Claude Code session in that project and inspect `/hooks` to check
registration. Submit `What is two plus two?`. The probe returns context asking
Claude to start with `LAYA_HOOK_CONNECTED`. Seeing that marker is a convenient
delivery check; model compliance is not guaranteed. Also inspect the newest
report and log for the actual invocation and emitted response. A successful
replay alone does not prove Claude received anything.

To stop the probe, remove only this command entry and start a fresh session.
Until removed, it runs for every submitted prompt in that project.

## What Claude sends and receives

Claude invokes the command before processing the submitted prompt and sends
event JSON on stdin. Among its fields are `hook_event_name`, `prompt`, and
`cwd`. Those describe the event, not Laya's question definitions or rules.
The probe emits this shape on stdout:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "Connection probe: LAYA_HOOK_CONNECTED ..."
  }
}
```

This adds context alongside the original prompt. It does not replace the prompt.
The live command prints only protocol JSON on stdout; readable reports go to
files. Errors use stderr. The existing real hook also redirects SDK progress
output to stderr to avoid corrupting stdout JSON. Text on stderr by itself does
not prove a crash; inspect the diagnostic and saved outcome.

Protocol reference: [Claude Code hooks](https://code.claude.com/docs/en/hooks).
This addition has not been run against a live Claude Code session here.

## What the existing real experiment does

`hook_user_prompt_submit.py` replays a saved event through the subprocess
`hooks/user_prompt_submit.py --real`. That hook invokes
`src/flows/file_method_context.py`: find the file, obtain
its outline, ask Laya to select a method and assess whether multiple methods
are required, apply acceptance rules, then collect context for an accepted
selection. A declined selection produces no additional context. Technical
failures also preserve the user's prompt; the diagnostic explains the cause.
Without the actual result file, a particular no-op cannot be diagnosed.

Where to edit each thing:

- Simulated Claude event: `experiments/inputs/hook_user_prompt_submit.json`.
- Question wording: `src/building_blocks/questions/method_selection/questions.json`.
- Acceptance conditions: the neighboring `rules.json`.
- Dynamic choices: neighboring `block.py` fills them from the file outline.
- Flow sequencing: `src/flows/file_method_context.py`.
- Model configuration: the real hook accepts `--config` with a RunConfig JSON;
  the replay script forwards its optional `--config` argument to the real hook.

Those question/rule files are shared by all callers of this block. Editing
them changes the real flow, not just the experiment. The event JSON currently
does not support overriding questions or rules. For isolated question edits,
use `laya_choice.py` and its input JSON; for rule decisions, the existing
`block_method_selection.py` experiment runs the shared block.

Start with the probe, then connect the real hook once delivery is confirmed.
Keep its diagnostic no-ops: forcing a method selection would hide the cause.
The real replay's default deadline is ten seconds, which can also expire during
cold model loading. Its existing `--deadline` option changes that limit.

## See the real questions, responses, and rule decisions

Run the real replay against one of the expanded fixture files:

```bash
python experiments/hook_user_prompt_submit.py --input experiments/inputs/hook_inventory.json --deadline 120
```

The replay prints the hook PID and debug-log path immediately. When the child
finishes, it prints the full question/choice payloads, requested model and
temperature, raw response, enriched answers, evaluated rules, decisions,
timeline, returned hook JSON, and stderr. It reads existing logs; it does not
query Laya again, recalculate enrichment, or change the acceptance rules.

Open the newest directory under `experiments/results/hook_user_prompt_submit/`:

- `summary.md`: the same readable report printed in the terminal.
- `details.json`: `laya_calls` holds the requests, responses, enrichment and
  decisions; `trace` holds the captured child log records; `stdout` and `stderr`
  retain the subprocess output.
- `trace.jsonl`: all captured Python log entries for this hook PID, starting at
  this replay's log offset. Previous runs and concurrent experiment PIDs are
  excluded. This is a copy, not a replacement for `logs/debug.jsonl`.

`request prepared` means the prediction boundary was reached, before loading
the model. `agent_ready` means loading or reuse completed. `response_received`
means a raw SDK response was logged. `response_validated` means the response
passed validation. A request without a response is not a successful model run.
If there is no recorded request, the report explicitly says so. Check the
timeline and diagnostics: the flow may have stopped at eligibility, file
resolution, extraction, or another earlier step. Missing/unreadable logging is
reported separately instead of being presented as proof that inference ran.

The trace is best-effort and reflects only emitted log entries. Raw child
stdout/stderr are retained separately, including native SDK progress. Logging
failures, file replacement, or abrupt termination can leave incomplete traces.
This report enhancement applies to the replay experiment; it does not install
new reporting in a live Claude session.

The real hook also logs these events with `component: hook`:

- `invoked` (`INFO`): hook processing started.
- `response_prepared` (`DEBUG`): full candidate response in `details.response`,
  plus `context_chars` and `max_context_chars`. This has not been sent yet.
- `context_size_warning` (`WARNING`): the formatted context exceeds the
  configured threshold (8,000 by default). Sizes are shown; the hook sends the
  full context unchanged. Historical runs used `response_rejected` (`ERROR`).
- `response_emitted` (`INFO`): the full JSON was written to stdout for Claude.
  This proves emission, not that Claude consumed it.
- `noop` (`INFO`): the flow declined context, with its reason.
- `failed` (`ERROR`): an exception stopped the hook; includes its traceback.

For a historical budget rejection, inspect `response_prepared` to see what would
have been returned. The actual response in those old runs is empty. Current
runs format the selected method and supporting source as readable text, keeping
raw hashes, diagnostics and generic limitations in the extraction logs. These
entries also appear in the replay's
`trace.jsonl` and execution timeline. Filter by `ERROR` to find hook failures.

Five ready event inputs target five different production files:

- `inputs/hook_inventory.json`: `consolidateOrderLines`.
- `inputs/hook_packing.json`: `PackingCalculator.countUnits`.
- `inputs/hook_pricing.json`: `insuranceCharge`.
- `inputs/hook_shipment.json`: `ShipmentService.checkAvailability`.
- `inputs/hook_reporting.json`: `renderShippingManifest`.

Use each with the same `--input` option. Edit its `prompt` to choose another
method. Keep the current flow's exact `Explain \`path.ts\`: question` format
and mention one file. Each target file has at least five implemented named
callables. The original default event and the connection probe remain available.
Laya can still decline a selection; richer fixtures and better reporting do not
force acceptance. The longer deadline only gives cold loading more time.

`hook_trace.py` is a reporting helper imported by the replay, not a runnable
experiment. Questions and rules still come from the existing method-selection
block described above. No new flow or model behavior is introduced here.
