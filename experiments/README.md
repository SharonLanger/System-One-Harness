# Experiments

## Copy a command and run it

Run these commands **from the repository root**, with your usual Python
environment activated. Choose one command at a time; each script is independent.
For IDE Play, run the script without arguments to use its default input. To use
an alternate input, put the flags below in the IDE's script arguments field.

**Start here: real Laya through the hook, using the expanded inventory file.**

```bash
python experiments/hook_user_prompt_submit.py --input experiments/inputs/hook_inventory.json --deadline 120
```

- `--input` selects the saved JSON event: edit its `prompt` to change the request.
- `--deadline 120` gives the hook 120 seconds for its work, including model
  loading and inference. It does not pause for 120 seconds when work finishes
  sooner. Without this flag the limit is 10 seconds, which may be too short for
  a cold model load. The replay allows another 10 seconds before killing the
  child; native SDK work may not stop immediately at the inner deadline.
- These flags belong to this replay script. Other scripts support only the
  flags shown below; `--deadline` is not a general Laya setting.

The replay prints questions, responses, enrichment, rules, and decisions after
the child finishes. Open the newest folder under
`experiments/results/hook_user_prompt_submit/`: `summary.md` is readable,
`details.json` contains the captured data, and `trace.jsonl` contains this hook
PID's log entries. A no-op can still have a complete model response and rejected
decision. If no request was observed, the report says so explicitly.

At the top of `summary.md`, **Hook output — what was actually returned** shows
whether the hook returned context. It includes the complete hook JSON and a
separate text box containing only the exact `additionalContext` value. For old
runs where the budget rejected a payload, both boxes are labeled **Prepared only
— NOT SENT**, with actual size and limit. Empty stdout is explained instead of showing
an unexplained `null`. Below the boxes are the selected method code and an
expandable view of all context fields, formatted for reading. These are display
changes only. The hook now uses a formatter to send readable method/supporting
code with paths and lines instead of the full internal extractor JSON.
Exceeding 8,000 formatted characters logs `WARNING` / `context_size_warning`
and still sends the full content. The old saved run reports remain historical
evidence; rerun an experiment to observe the new behavior.

The current context formatter uses plain text and paths relative to the hook
event's cwd. It keeps the same code, supporting declarations, line ranges and
notes. Report files remain Markdown for viewing; the `additionalContext` string
has no formatter-added headings, fences or bullet prefixes. See the separate
[future helper plan](../docs/call-navigation-plan.md) for outgoing/incoming
navigation methods that are not yet implemented or used by a flow.

**Try the other four files with the same hook:**

```bash
python experiments/hook_user_prompt_submit.py --input experiments/inputs/hook_packing.json --deadline 120
python experiments/hook_user_prompt_submit.py --input experiments/inputs/hook_pricing.json --deadline 120
python experiments/hook_user_prompt_submit.py --input experiments/inputs/hook_shipment.json --deadline 120
python experiments/hook_user_prompt_submit.py --input experiments/inputs/hook_reporting.json --deadline 120
```

Omit `--input` to use the original `inputs/hook_user_prompt_submit.json`.
Optional `--config /absolute/path/run-config.json` supplies the hook's model
configuration, with `model`, `temperature`, and `lang` fields. This is separate
from the event input. Replaying does not register a live Claude hook.

**Connection probe only — no Laya, questions, or rules:**

```bash
python experiments/hook_prompt_probe.py
```

Edit `inputs/hook_prompt_probe.json` to change the marker message or synthetic
event. Optional `--config /path/probe.json` selects another probe configuration;
this is not a model configuration. `--hook` is for the live Claude command and
waits for event JSON on stdin, so do not add it for a normal Play/replay run.
See [live setup](HOOKS.md#connect-it-on-your-mac).

**Direct Laya calls — choose a question type:**

```bash
python experiments/laya_choice.py
python experiments/laya_noul.py
python experiments/laya_score.py
python experiments/laya_multiple_questions.py
python experiments/laya_compare_models.py
```

Edit the matching `experiments/inputs/<script-name>.json` for questions, text,
and configuration. These scripts do not accept `--input`. They accept `--model`,
`--temperature`, and `--lang` overrides. For example:

```bash
python experiments/laya_choice.py --temperature 0.2
python experiments/laya_compare_models.py --temperature 0.2 --compare-temperature 0.7
```

To select another compatible checkpoint, add `--model "YOUR_MODEL_ID"`;
comparison also supports `--compare-model "YOUR_SECOND_MODEL_ID"`. Replace those
placeholders with real model IDs. The comparison script makes two requests.

**One building block — questions, enrichment, rules, and method selection:**

```bash
python experiments/block_method_selection.py
python experiments/block_method_selection.py --temperature 0.2
```

Edit `inputs/block_method_selection.json` for the prompt and synthetic outline.
This script also accepts `--model` and `--lang`, but not `--input`. Questions and
rules are loaded from the shared method-selection block, as [explained here](HOOKS.md#what-the-existing-real-experiment-does).

**Complete file/method flows — default, controller, or static method:**

```bash
python experiments/flow_method_context.py
python experiments/flow_connected_project.py
python experiments/flow_connected_project.py --input experiments/inputs/flow_connected_project_controller.json
python experiments/flow_connected_project.py --input experiments/inputs/flow_connected_project_static.json
```

Both flow scripts accept `--input`. Their JSON uses `text` and `config`, unlike
hook event JSON, which uses `prompt`, `cwd`, and `hook_event_name`. Do not swap
these two input formats. Change model settings in the flow input's `config`.

**Repeat prompts, or intentionally try a missing file:**

```bash
python experiments/repeat_scenario.py
python experiments/flow_missing_file.py
```

Edit their matching input JSON files; neither script accepts CLI options.
The repeat script calls real Laya for each prompt (up to five). The missing-file
script intentionally produces a no-op without calling Laya.

**Prerequisites for file extraction:** install Node dependencies once with
`npm --prefix typescript-helper ci`, then run
`npm --prefix typescript-helper run build`. Build again after helper source
changes; no rebuild is needed just to edit prompts. This applies to file flows
and real hook replay. The connection probe and static-outline block do not need
Node. Model-calling experiments need your working `laya_mlx`/MLX environment.

**Helpers, not experiments:** `experiment_runner.py`, `support.py`, `summary.py`,
`block_method_selection_summary.py`, and `hook_trace.py` are imported by the
scripts above. Do not run them to launch experiments.

To understand the prompt hook and first check the live Claude connection, see
[the hook guide](HOOKS.md). Run `hook_prompt_probe.py` for a simple, configurable
context response with immediate invocation logging and no Laya call. Its
`--hook` mode accepts Claude's stdin; its default mode replays a synthetic event.

For actual Laya questions and responses, use `hook_user_prompt_submit.py`.
Its terminal output and saved report now include questions, raw responses,
enrichment, evaluated rules and decisions, plus a per-hook-PID `trace.jsonl`.
The [expanded fixture](fixtures/connected_project/README.md) adds five production
files with five implemented methods/functions each. See [the hook guide](HOOKS.md#see-the-real-questions-responses-and-rule-decisions)
for five ready replay inputs and how to identify a run that never reached Laya.

Direct adapter experiments are implemented for choice, noul, score, multiple
named questions, and configuration comparison. No live Laya execution is
verified here. See [the implementation plan](../docs/experiments-plan.md). A mock
run does not count as a completed real experiment.

The first building-block experiment is `block_method_selection.py`. It passes a
clearly synthetic request and callable outline to the existing method-selection
block, which constructs its dynamic questions, submits one model request, and
applies the block's existing acceptance rules. The candidate signatures,
synthetic path, and source hash in `inputs/block_method_selection.json` do not
describe a real source file. The outline is static JSON input: no Node build or
source scan is required. Its default prompt asks about one callable; edit the
synthetic `text` field to explore a request that may require multiple methods.
Reports capture the exact submitted question payload, raw SDK response,
enriched response when possible, per-question
decisions and rule reasons, and final selected candidate or no-op reason. A
pre-inference no-op has no captured questions or raw response; a technical
failure is recorded with its stage and error.

An experiment is a manually runnable Python script exercising an existing
project entry point with explicit synthetic inputs. Experiments use real Laya
on Sharon's Mac; automated tests inject mocks. They do not change production
flow behavior or activate Claude hooks.

## Names identify where execution starts

- `laya_<scenario>.py`: calls the existing Laya adapter, which loads/reuses the
  agent, predicts, and validates its response. No enrichment or rule evaluation.
- `block_<scenario>.py`: calls an existing question building block, including
  its question preparation and rule processing.
- `flow_<scenario>.py`: calls an existing flow, including its supported branches.
- `hook_<event>.py`: supplies saved event JSON to the actual hook subprocess.
  Replay does not establish delivery to a running Claude session.
- `repeat_scenario.py`: later orchestration of repeated scenario calls with
  explicit input variations; not a new production workflow engine.

The suffix describes the question type or scenario. Use the SDK spelling
`noul`. Available direct adapter scripts are `laya_choice.py`, `laya_noul.py`,
`laya_score.py`, `laya_multiple_questions.py`, and `laya_compare_models.py`.

## Locations

For `laya_noul.py`:

```text
experiments/laya_noul.py
experiments/inputs/laya_noul.json
experiments/results/laya_noul/2026-10-30_14-32-05/summary.md
experiments/results/laya_noul/2026-10-30_14-32-05/details.json
```

The results subfolder normally equals the script stem. `flow_method_context.py`
uses the input filename stem when passed `--input`; `flow_connected_project.py`
and hook replay keep their script stem for alternate inputs. Each run has its own
directory named `YYYY-MM-DD_HH-MM-SS`, using the Mac's local time. Same-second
collisions use `_001`, `_002`, etc., allocated without overwriting another run.
Store the timezone offset and UTC start time in the report too. Directory names
sort chronologically under an unchanged local clock; daylight-saving or manual
clock changes require comparing the recorded UTC timestamps.

`results/` and captured personal hook inputs must be ignored by Git. Commit only
synthetic, shareable sample inputs. Default inputs are located relative to the
script. Explicit relative `--input`/`--config` paths are relative to your current
shell directory; use absolute paths when running elsewhere.

## Input and configuration

Direct Laya input JSON contains `text`, named `questions`, and `config`:

```json
{
  "text": "I ate an apple.",
  "questions": {
    "fruit": {
      "type": "choice",
      "instructions": "Which fruit is mentioned?",
      "criteria": {"apple": "apple", "pear": "pear"}
    }
  },
  "config": {
    "model": "aac6fef/laya-typed-decisions-mlx",
    "temperature": null,
    "lang": "en"
  }
}
```

Change `config.model` and `config.temperature` to try compatible configurations
in the same script. Null temperature means SDK default, not zero. Optional CLI
overrides take precedence over the input file; the report records resolved
requested settings. For direct scripts, `--model`, `--temperature`, and `--lang`
are supported.

`laya_multiple_questions.py` submits all named question definitions in one
adapter call. `laya_compare_models.py` submits the same text and questions twice
through one registry. Its default `comparison_config: null` repeats the primary
configuration to demonstrate registry reuse. Supply a compatible
`comparison_config` in the input or use `--compare-model`,
`--compare-temperature`, or `--compare-lang` to compare a second configuration.
No second checkpoint is assumed to exist.

Use existing `RunConfig` and `AgentRegistry`. The current adapter passes an
explicit temperature via `lang_temperatures[lang].temperature = [t, t, t]` on
load, and passes `lang` on prediction. With null temperature it passes neither
override. This is the repository's current behavior; real SDK compatibility and
supported temperature ranges remain unverified. Do not silently change this
mapping or invent a second checkpoint.

## What a run shows

Terminal output shows progress, requested model and temperature (`SDK default`
when null), raw response, final answer, and saved report paths. `summary.md` is
the readable report: it states the requested model, temperature, and language;
shows the input text and each question's exact instructions and criteria; then
describes each answer by type. Choice reports show the selected choice and its
probabilities, noul reports show the numeric value, and score reports show the
raw score and legend. Multiple-question reports add a compact answer table.
Comparison reports show both configurations and outcomes and record whether
the registry returned the same agent object. Confidence fields appear when the
response provides them. Failure reports identify the stage and error and show
captured raw data when available; large raw data stays in `details.json`.

`details.json` remains the structured source of truth. Reports preserve input,
submitted questions, requested settings, raw response, final result, timing,
processing state, and errors. Requested settings do not prove the actual
checkpoint or effective SDK temperature. Basic adapter calls mark enrichment
and rules as `not_run`; the summary describes that the call was direct and did
not run enrichment or rules.

Success means the request and response contract worked, not that the model chose
an expected semantic answer. Errors are reported visibly and return a nonzero
exit code. Available evidence is saved on loading, inference, or validation
failures. Saving failures are reported and never described as saved. There is no
mock fallback. Imports do not load models or run scenarios; a caller may provide
a registry for reuse within one invocation.

## Run an experiment

Activate the Python 3.11+ environment containing the installed `laya_mlx` SDK
and compatible MLX. The scripts bootstrap this checkout's `src/` import path, so
installing the project with `pip install -e .` is optional. Run from any working
directory, for example:

```bash
python /path/to/laya-context-router/experiments/laya_noul.py
```

The script reads its matching file under `inputs/` and writes a unique report
under `experiments/results/<script-stem>/`. In an IDE, select the same Python
environment and run the script with no arguments. Live compatibility is
unverified; missing SDK/model errors are reported without a mock fallback.
Keep private captures out of Git.

## Flow, hook replay, and repeated scenario experiments

`flow_method_context.py` runs the existing file-method context flow against
`fixtures/synthetic_method.ts`. Its prompt, model configuration, and fixture
are synthetic. It records the final `context` or `noop` result and, when the
flow reaches prediction, captures the exact submitted question payload and raw
SDK response through the observed registry. A no-op is a valid flow outcome.
The TypeScript helper is a prerequisite: from the repository root, run
`npm --prefix typescript-helper install` and
`npm --prefix typescript-helper run build` before running this flow. The
experiment does not build it automatically. A Python 3.11+ environment
with `laya_mlx`, compatible MLX, and Node.js are also required.

`flow_connected_project.py` runs the same flow against the deterministic
multi-file fixture in `fixtures/connected_project/`. Its default prompt selects
`calculateInvoiceTotal` in `invoice-service.ts`; that function imports
`calculateAdjustment`, which calls `addOne`, `double`, and `subtract`, and uses
project constants and other imported helpers. `tsconfig.json` explicitly uses
CommonJS and Node10 resolution and includes both `src/**/*.ts` and
`tests/**/*.spec.ts`. The spec files use self-contained assertions and need no
test framework. The controller and currency formatter inputs exercise
instance-method and static-method entry points:
`inputs/flow_connected_project_controller.json` and
`inputs/flow_connected_project_static.json`. These are useful probes for
collector limits around class/static dispatch and member calls. The fixture
does not imply that every edge will be resolved; inspect `dependencies`,
`gaps`, and `limitations` in each run's `details.json`.

The flow scripts accept `--input /path/to/input.json` to try another saved
prompt/configuration. Report-folder naming is described under Locations above,
with a timestamped summary and details file. For example, run the direct imported
function chain from any working directory with:

```bash
python /path/to/laya-context-router/experiments/flow_connected_project.py
```

`flow_missing_file.py` is the deterministic missing-`.ts`-file reference
branch. It records the existing flow's missing-file no-op reason and makes no
model call.

`hook_user_prompt_submit.py` replays the saved synthetic
`inputs/hook_user_prompt_submit.json` event through the actual hook subprocess.
The script replaces `cwd` only when it equals `__REPOSITORY_ROOT__`; a captured
cwd is otherwise preserved. Pass `--input /path/to/event.json` to replay another
saved event. It supplies `src/` through `PYTHONPATH`, and saves stdout, stderr,
exit status, and context/no-op/technical-error classification. A captured cwd
outside this repository is preserved and the hook will no-op. The replay does
not install or activate Claude hooks.
The TypeScript helper build, Node.js, `laya_mlx`, and compatible MLX are also
required for a context-producing run; the hook itself catches failures and may
report a no-op with exit status zero. The replay classifies known flow no-op
reasons separately from technical-error messages in stderr.
The hook deadline defaults to 10 seconds, matching the hook's own default;
use `--deadline SECONDS` to allow more time for a cold model load. The replay
subprocess timeout is set to the chosen deadline plus 10 seconds.

`repeat_scenario.py` sends one named `fruit` choice question for each prompt in
`inputs/repeat_scenario.json`, using one real `AgentRegistry` instance in the
process. The input is capped at five prompts (three by default). The report
contains each selected choice or error and an aggregate count; it makes no
accuracy claim.

Run these scripts from any directory after prerequisites are met:

```bash
python /path/to/laya-context-router/experiments/flow_method_context.py
python /path/to/laya-context-router/experiments/flow_missing_file.py
python /path/to/laya-context-router/experiments/hook_user_prompt_submit.py
python /path/to/laya-context-router/experiments/repeat_scenario.py
```

Reports are saved under the matching `experiments/results/<script-stem>/`
directory, with a timestamped `summary.md` and `details.json` for each run.


## Debug log

All experiment layers append to `logs/debug.jsonl` at the repository root.
Run any experiment as usual; no flag or setup is needed. Each JSONL line has
time (including timezone), level, PID, parent PID, component, event, and details.
The experiment's `details.json` run metadata and saved `summary.md` identify
its PID and log path. The first log event names the experiment script.

Ordinary experiments run in one Python process. Hook replay launches a child
Python process, whose parent PID links it to the experiment. The Node extractor
is logged at its Python subprocess boundary, including its request, stdout and
stderr. Therefore all processes use one file rather than separate PID files.
PIDs can be reused by the OS: use the timestamp and experiment started event
when looking at older runs.

Search for `"component": "extractor"` or `"level": "ERROR"` to investigate
`extractor_error`. Logs include the helper path, target file, request, raw helper
output, validated outline/context, and original exceptions with tracebacks.
`helper_returned` means the subprocess returned; `outline_validated` or
`context_validated` means its data passed validation. A missing next event helps
locate where execution stopped.

Question logs show loaded definitions/rules and the prepared dynamic payload.
Laya logs show requested settings, agent load/reuse and raw responses.
Enrichment logs show added properties and the enriched prediction; rule logs
show the conditions evaluated and the extracted answer/acceptance reason.
Flow logs record the selected method and final context/no-op status.

This is simple local debugging: all levels are written, with no rotation,
server, new flow context, or change to selection rules. Entries can contain full
prompts, model responses and source code; `logs/` is ignored by Git. Delete the
file whenever desired. Logging is best effort: a file-write failure must not
change the flow result, and logging writes nothing to hook stdout.

