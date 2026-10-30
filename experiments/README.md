# Experiments

Status: `laya_choice.py` is implemented as the first runnable experiment. The
noul and score scripts remain planned; no real Laya execution is verified here.
See [the implementation plan](../docs/experiments-plan.md). This README defines
the intended convention. Do not report a planned script or a mock test as a
completed real experiment.

An experiment is a small, manually runnable Python script exercising an existing
project entry point with explicit inputs. It prints readable progress and saves
evidence. Experiments use real Laya on Sharon's Mac; automated tests inject mocks.
They do not change production flow behavior or activate Claude hooks.

## Names identify where execution starts

- `laya_<scenario>.py`: calls the existing Laya adapter, which loads/reuses the
  agent, predicts, and validates its response. No enrichment or rule evaluation.
- `block_<scenario>.py`: calls an existing question building block, including its
  question preparation and rule processing.
- `flow_<scenario>.py`: calls an existing flow, including its supported branches.
- `hook_<event>.py`: supplies saved event JSON to the actual hook subprocess.
  Replay does not establish delivery to a running Claude session.
- `repeat_scenario.py`: later orchestration of repeated scenario calls with
  explicit input variations; not a new production workflow engine.

The suffix describes the question type or scenario. Use the SDK spelling `noul`.
First planned scripts: `laya_choice.py`, `laya_noul.py`, and `laya_score.py`.

## Locations

For a script named `laya_choice.py`:

```text
experiments/laya_choice.py
experiments/inputs/laya_choice.json
experiments/results/laya_choice/2026-10-30_14-32-05/summary.md
experiments/results/laya_choice/2026-10-30_14-32-05/details.json
```

The results subfolder always equals the script stem. Each run has its own
directory named `YYYY-MM-DD_HH-MM-SS`, using the Mac's local time. Same-second
collisions use `_001`, `_002`, etc., allocated without overwriting another run.
Store the timezone offset and UTC start time in the report too. Directory names
sort chronologically under an unchanged local clock; daylight-saving or manual
clock changes require comparing the recorded UTC timestamps.

`results/` and captured personal hook inputs must be ignored by Git. Commit only
synthetic, shareable sample inputs. Inputs are read relative to the script, not
the shell working directory. On your Apple Silicon Mac, select the Python
environment where `laya_mlx` is installed, then from the repository root run
`python -m pip install -e .` once. Open `laya_choice.py` in a Python-capable IDE
and press Run, or execute `python experiments/laya_choice.py`. To override model
and temperature for a run, use `--model YOUR_MODEL --temperature YOUR_TEMPERATURE`
with a checkpoint and temperature confirmed compatible with your SDK. Edit the
input JSON's temperature to `null` to return to SDK defaults. The IDE needs
Python execution support and that environment selected.

## Input and configuration

Each first-stage input JSON contains `text`, named `questions`, and `config`:

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
in the same script. Null temperature means SDK default, not zero. An optional
CLI override should have precedence over the input file; the report records the
resolved configuration. No-argument execution uses the matching input file.

Use existing `RunConfig` and `AgentRegistry`. The current adapter passes an
explicit temperature via `lang_temperatures[lang].temperature = [t, t, t]` on
load, and passes `lang` on prediction. With null temperature it passes neither
override. This is the repository's current behavior; real SDK compatibility and
supported temperature ranges remain unverified. Do not silently change this
mapping or invent a second checkpoint. Sharon may provide a corrected example.

## What a run shows

Terminal progress: starting, loading/reusing agent, sending questions, receiving
response, outcome, and saved report paths. Always display requested model and
temperature (`SDK default` when null). Use plain text without requiring colors.

`summary.md` is the human-readable view: input, question definitions, requested
settings, response, applicable processing, final outcome, timings, and errors.
`details.json` is the structured source of truth, with these top-level sections:

- `run`: script, entry point, report schema version, timestamps, duration,
  execution mode, and technical status.
- `input`: actual text submitted.
- `questions`: actual named question payload submitted.
- `model_config`: resolved requested model, temperature, and language; separately
  labeled observed metadata when safely available. Requested settings are not
  proof of the actual checkpoint or effective SDK temperature.
- `raw_response`: original JSON response, when received.
- `processing`: enrichment and rules, each explicitly `not_run`, `available`,
  or `not_exposed`. The first three scripts use `not_run`.
- `result`: concise view of the returned choice, noul value, or score. For basic
  calls, do not invent acceptance decisions or convert noul using new rules.
- `error`: null on technical success; otherwise stage, exception type, and message.

Success means the request and response contract worked, not that the model chose
an expected semantic answer. Report errors visibly and return a nonzero exit
code for technical failures. Save available evidence even if loading, inference,
or validation fails. Never silently fall back to a mock. If saving itself fails,
print the error and never claim the results were saved.

Later entry points may expose only a final result. Mark missing intermediate
data `not_exposed`; do not rerun the model or alter flows to fabricate a trace.
Aggregation and alternative summary layouts can later consume the same reports.

## Instructions for agents

To answer “summarize the latest laya choice,” locate
`results/laya_choice/`, identify the latest run by its recorded start time, read
`summary.md`, and use `details.json` for exact data. Include failed runs when
choosing latest unless the user explicitly asks for latest successful. If no
results exist in the checkout, say so; local ignored results do not sync via Git.
Do not launch another real inference merely to retrieve a previous result.

To add an experiment, choose the prefix for the actual entry point, add its
matching input file, expose `run(...)` plus `main()`, reuse the small output
helper, add boundary tests, and update this README. Imports must not load models
or run scenarios. A caller may supply a registry for reuse within one invocation.
Use existing project functionality; document unsupported behavior before proposing
any production change.

## Run the first experiment

On Sharon's Apple Silicon Mac, activate the Python 3.11+ environment containing
the supplied `laya_mlx` SDK and compatible MLX. From the repository root, install
the project into that environment once, then run:

```bash
python -m pip install -e .
python /path/to/laya-context-router/experiments/laya_choice.py
```

The script reads its adjacent `inputs/laya_choice.json` and writes a unique
timestamped report under `experiments/results/laya_choice/`. In an IDE, open
`laya_choice.py`, select that Python environment, and use Run File. Optional
`--model`, `--temperature`, and `--lang` arguments override the input settings;
edit temperature to `null` in the input file to request SDK default. With no
test loader injected, the script always uses the real adapter and reports missing
SDK/model errors without a mock fallback. Automated tests use synthetic SDK
responses and do not verify live compatibility. Keep private captures out of Git.

## Later scenarios to remember

- Multiple questions in one call; model and temperature comparisons.
- One building block, then the existing method-context flow.
- Missing file and nonexistent method references: show the actual no-op reason.
- A genuine controlled technical failure: show error stage and diagnostics.
  A no-match/no-op is not itself a technical error.
- Hook replay using a synthetic event, then Sharon's captured event; actual Claude
  hook installation and end-to-end delivery are a separate later step.
- Repetition with changing prompts/questions, agent reuse, individual outcomes,
  and an aggregate summary. Decide this report extension when implementing it.

After the first scripts are pushed and Sharon tries them, explicitly revisit the
bad-method and visible-error scenarios before proceeding to hook integration.
