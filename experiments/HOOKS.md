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
`src/laya_context_router/flows/file_method_context.py`: find the file, obtain
its outline, ask Laya to select a method and assess whether multiple methods
are required, apply acceptance rules, then collect context for an accepted
selection. A declined selection produces no additional context. Technical
failures also preserve the user's prompt; the diagnostic explains the cause.
Without the actual result file, a particular no-op cannot be diagnosed.

Where to edit each thing:

- Simulated Claude event: `experiments/inputs/hook_user_prompt_submit.json`.
- Question wording: `src/laya_context_router/building_blocks/questions/method_selection/questions.json`.
- Acceptance conditions: the neighboring `rules.json`.
- Dynamic choices: neighboring `block.py` fills them from the file outline.
- Flow sequencing: `src/laya_context_router/flows/file_method_context.py`.
- Model configuration: the real hook accepts `--config` with a RunConfig JSON;
  the existing replay script currently does not expose that argument.

Those question/rule files are shared by all callers of this block. Editing
them changes the real flow, not just the experiment. The event JSON currently
does not support overriding questions or rules. For isolated question edits,
use `laya_choice.py` and its input JSON; for rule decisions, the existing
`block_method_selection.py` experiment runs the shared block.

Start with the probe, then connect the real hook once delivery is confirmed.
Keep its diagnostic no-ops: forcing a method selection would hide the cause.
The real replay's default deadline is ten seconds, which can also expire during
cold model loading. Its existing `--deadline` option changes that limit.
