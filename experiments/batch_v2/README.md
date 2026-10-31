# Runner V2 (RV2)

Status: design-stage documentation. PR #21 contains the plan and these guides. The `run.py`, `collect.py`, example files and report generator described below are implementation deliverables and are not available yet. Commands below define the intended interface; they have not been executed against an RV2 implementation.

RV2 runs one experiment's question variants × rules × named configurations against the same input cases, then compares the outcomes. Each combination sees each case once; there are no repetitions. Create another experiment by writing two JSON files, using the same runner.

- [Input and experiment authoring guide](input-authoring.md): complete cases.json and suite.json examples, label status, noise levels, tags and annotation workflow.
- [Implementation design](runner-v2-plan.md): execution, checkpoint/resume, output schema, scoring formulas and verification requirements.

## What you create

Create `experiments/batch_v2/experiments/<experiment-id>/` containing:

- `cases.json`: input cases, expected labels and annotations.
- `suite.json`: the task's fixed question type and labels, question variants, rules, configurations and baseline IDs.

Use one classification task per experiment. All variants retain the question type, canonical label IDs, label meanings and choice order. Change wording or choice descriptions slightly. Changing from `choice` to `noul`, or changing what the classes mean, requires a separate experiment.

Generic experiments take string inputs and need no custom runner code. The requested-action and context-scope adapters take the objects required by their existing blocks. The authoring guide shows those distinctions. Expected labels and annotations never go to the model.

## Planned first run

After implementation, use the existing repository Python environment from the repository root. Live mode additionally requires a compatible Mac environment with `laya_mlx`, MLX and the selected model already installed/cached. The runner does not install packages or download models automatically. Fixture mode will not require MLX or model weights.

First run the shipped synthetic example:

```bash
python experiments/batch_v2/run.py --cases experiments/batch_v2/examples/generic-choice/cases.json --suite experiments/batch_v2/examples/generic-choice/suite.json --mode fixture --rule-mode replay
```

This example is required to produce 8 vectors and 24 logical result rows from 2 questions × 2 rules × 2 configurations × 3 cases, backed by 12 synthetic inference records in replay mode. It checks plumbing and reporting, not model accuracy. Its fixture responses must be shipped with the implementation. IDE Play on its launcher will select this explicitly labeled fixture example.

## Planned workflow for your experiment

After saving the two files under `experiments/batch_v2/experiments/fruit-smoke/`, validate them without loading a model:

```bash
python experiments/batch_v2/run.py --cases experiments/batch_v2/experiments/fruit-smoke/cases.json --suite experiments/batch_v2/experiments/fruit-smoke/suite.json --validate-only
```

Inspect matrix size and input distribution without predictions:

```bash
python experiments/batch_v2/run.py --cases experiments/batch_v2/experiments/fruit-smoke/cases.json --suite experiments/batch_v2/experiments/fruit-smoke/suite.json --dry-run
```

Run live with a direct invocation for each vector/case:

```bash
python experiments/batch_v2/run.py --cases experiments/batch_v2/experiments/fruit-smoke/cases.json --suite experiments/batch_v2/experiments/fruit-smoke/suite.json --mode live --rule-mode direct
```

Once replay parity has been verified for the selected adapter and question type, use `--rule-mode replay` to evaluate different rules on the same inference. For this example direct mode requires 24 inference calls and replay requires 12; both create 24 logical outcomes. Unsupported replay must fail clearly instead of claiming a verified optimization. The two rule modes differ in whether rules see shared evidence or independent predictions.

Live predictions are not promised to match the expected labels. For a new dataset, expected labels are independently reviewed ground truth, not the results of an earlier run copied back into the inputs.

## Where results go

Each launch prints a new folder under:

`experiments/batch_v2/results/<experiment-id>/<UTC-timestamp>__<unique-id>/`

Open `report.html` locally for interactive vector/group filtering, or `comparison.md` for a readable text report. The local HTML needs no server or network. For programmatic analysis, read `results.jsonl` (one row per vector/case) and `summary.csv` (one row per vector/group).

The folder also includes `manifest.json`, `inferences/` and detailed case checkpoints under `batches/<question-id>__<rule-id>/<config-id>/cases/`. The manifest freezes the exact input definitions/settings. Inference records preserve the raw model evidence; case records preserve the rule decision.

The main table compares vectors. Selecting one vector shows the same metrics for all inputs, each noise level, and each tag. Correct/wrong final answers and abstentions are separate; abstentions are split into correct answers rejected and wrong answers filtered. Read scored and unscored counts alongside accuracy. Noise levels partition the dataset; tags may overlap and must not be summed.

## Resume and regenerate reports

These commands use the printed run-folder path; replace the placeholder before running:

```bash
python experiments/batch_v2/run.py --resume <existing-run-folder>
python experiments/batch_v2/collect.py --run <existing-run-folder>
```

Resume uses the frozen definition and completes missing work only if the required hashes/mode match. Editing questions, cases, rules or configurations means starting a new run. Collector rebuilds reports without running a model. Ctrl+C preserves completed checkpoints; unfinished cases remain explicitly unattempted.

Errors, timeouts and skipped/unattempted inputs are technical statuses, not wrong answers or abstentions. An incomplete run remains visibly partial. The implementation must document exact supported runtime-limit flags and failure exit codes here after they are implemented and verified.

## Documentation handoff

At implementation completion, replace this design-stage status with verified setup/commands, ship the referenced example and IDE launcher, run the fixture example and applicable checks, and report any remaining live-only verification. Until then these commands are specifications, not claims of runnable software.
