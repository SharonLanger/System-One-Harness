# LAYA batch experiments

Run one fixed question against ten labeled inputs, then repeat the same cases for each named model configuration. IDE Play on `run.py` defaults to `apple-choice`.

```bash
python experiments/batch/run.py --experiment apple-choice
python experiments/batch/run.py --experiment apple-noul
python experiments/batch/run.py --experiment apple-choice --configuration sdk-default
```

Use your existing Mac Python 3.11+ environment with `laya_mlx`, MLX and the model already installed/cached. No Node build or package installation is performed. The runner locates the cached `rl_agent_config.json` without a network request, preserves its snapshot directory, and passes that local directory to the SDK with `local_files_only=True`. It checks `rl_agent_config.json`, `encoder/config.json` and `model.safetensors`; the SDK validates tokenizer assets and file contents. Missing repository-only files such as LICENSE or README do not block loading. Missing SDK/cache files are recorded as configuration errors, shown separately from case errors in the comparison. A load failure means zero attempted cases and no model recommendations; unattempted cases are not abstentions. Live SDK compatibility, including local-path loading and temperature behavior, must be verified on your Mac. Requested settings are not proof of effective SDK settings.

Each experiment folder contains one `experiment.json`: one named `question`, one `rule`, a list of `{id,input,expected}` cases, and a list of named `{name,model,temperature,lang}` configurations. The examples use SDK default (`null` temperature), 0.2 and 0.7 on the existing model. Null does not mean zero. Add another compatible, locally available model by adding a named configuration. Names use lowercase letters, digits, hyphens or underscores; `comparison` is reserved. Unknown settings and duplicate keys are rejected. SDK-default temperature supports only `lang: en` because the existing adapter omits language forwarding in that mode; use an explicit temperature for another language. Rule conditions use the existing `field`, `op`, `value` format.

`choice` selects apple, pear, dog or other. `noul` answers whether there is clear apple-fruit evidence, with yes/no labels. `noul` is the SDK spelling, distinct from JSON null. The cases intentionally include apple descriptions, vague fruit wording and Apple computers. Expected labels are editable synthetic ground truth; case 09 is the intended conventional apple description. Generic fruit is no positive apple evidence. Thresholds are illustrative, not calibrated.

The expected label never goes into the SDK request. One configuration runs all cases sequentially with one reused agent. Configurations run in separate sequential processes, releasing model memory after each. There is no retry or mock fallback. Each experiment makes 30 predictions across the three configurations; both make 60. An accepted different label is incorrect; undecided is an abstention; malformed responses and processing failures are errors. Valid `other` is a normal class. Raw recommendations and rule decisions are scored separately.

## Results

Each execution creates `results/YYYY-MM-DD_HH-MM-SS/` under its experiment, in Israel local time. Collisions receive `_001` and so on. UTC timestamps and offsets are also recorded. All generated results are ignored by the local `.gitignore`.

- `comparison.md`: configuration metrics, rule effects and cases that changed.
- `<configuration>.md`: readable summary, case outcomes and threshold diagnostics.
- `<configuration>.json`: full definition snapshot/hash, requested settings, raw responses, actual interpreter enrichment and trace events, recommendations, decisions, metrics, errors and timing.

JSON is checkpointed after each case using atomic replacement. Runtime logs are captured into that JSON; a temporary `.trace.tmp` file may remain after a hard interruption. Completed cases remain available after interruption. Unattempted cases stay separate. Saving or technical failures return a nonzero exit code; model mistakes alone do not. Ctrl+C stops the current worker, preserves its last checkpoint, and marks remaining configurations unattempted. There is no resume function or default time limit; a stalled SDK call can be stopped with Ctrl+C.

Accuracy uses definitive answers as denominator. Coverage uses attempted cases. Reports also show all outcome counts and rates among attempted cases, with N/A when a denominator is zero. Completed configurations are ranked by fewer wrong final answers, then fewer abstentions. Incomplete configurations are not best-result candidates. Results measure this dataset only.

Condition margins are derived report calculations: observed minus lower threshold, or upper threshold minus observed. Zero passes inclusive comparisons only; missing values have no margin. Runtime enrichment uses the existing rounding behavior. Each condition is shown individually, not combined into an invented confidence number.

All task-owned code, reports, logs, temporary files and checks stay under `experiments/`; production modules are imported read-only. Bytecode output is disabled before repository imports. External SDK/model cache behavior remains SDK-owned; offline mode prevents deliberate downloads.

## Mechanical verification

```bash
python -B -m unittest discover -s experiments/batch/checks -v
```

These checks use explicitly injected responses, exercise the existing validators/interpreter, and never load the real SDK. Temporary results are below `checks/output/`. They verify bookkeeping and execution behavior, not model accuracy. Real inference is a separate manual check on the Mac.
