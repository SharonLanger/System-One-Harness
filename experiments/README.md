# Experiments

Direct adapter experiments are implemented for choice, noul, score, multiple
named questions, and configuration comparison. No live Laya execution is
verified here. See [the implementation plan](../docs/experiments-plan.md). A mock
run does not count as a completed real experiment.

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
the human-readable view; `details.json` is the structured source of truth.
Reports preserve input, submitted questions, requested settings, raw response,
final result, timing, processing state, and errors. Requested settings do not
prove the actual checkpoint or effective SDK temperature. Basic adapter calls
mark enrichment and rules as `not_run`.

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

## Later scenarios to remember

- One building block, then the existing method-context flow.
- Missing file and nonexistent method references: show the actual no-op reason.
- A genuine controlled technical failure: show error stage and diagnostics.
  A no-match/no-op is not itself a technical error.
- Hook replay using a synthetic event, then Sharon's captured event; actual Claude
  hook installation and end-to-end delivery are a separate later step.
- Repetition with changing prompts/questions, agent reuse, individual outcomes,
  and an aggregate summary. Decide that report extension when implementing it.

After the first scripts are pushed and Sharon tries them, explicitly revisit the
bad-method and visible-error scenarios before proceeding to hook integration.
