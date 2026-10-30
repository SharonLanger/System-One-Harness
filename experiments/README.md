# Experiments

To understand the prompt hook and first check the live Claude connection, see
[the hook guide](HOOKS.md). Run `hook_prompt_probe.py` for a simple, configurable
context response with immediate invocation logging and no Laya call. Its
`--hook` mode accepts Claude's stdin; its default mode replays a synthetic event.

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

The results subfolder always equals the script stem. Each run has its own
directory named `YYYY-MM-DD_HH-MM-SS`, using the Mac's local time. Same-second
collisions use `_001`, `_002`, etc., allocated without overwriting another run.
Store the timezone offset and UTC start time in the report too. Directory names
sort chronologically under an unchanged local clock; daylight-saving or manual
clock changes require comparing the recorded UTC timestamps.

`results/` and captured personal hook inputs must be ignored by Git. Commit only
synthetic, shareable sample inputs. Inputs are read relative to the script, not
the shell working directory.

## Input and configuration

Each input JSON contains `text`, named `questions`, and `config`:

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
prompt/configuration. Reports go under the invoking script's own stem, with a
timestamped summary and details file. For example, run the direct imported
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

