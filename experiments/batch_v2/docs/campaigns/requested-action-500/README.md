# Start here: requested action, 500 inputs

This experiment asks: **Does the user want an explanation, additional tests, or a code change?** A campaign simply means the successive runs we use to investigate that one question with the same frozen inputs.

Status: first round prepared; no LAYA research results yet. Live execution requires the existing Mac SDK and cached model. Preparation and offline checks do not establish live capability.

## Run it

From the repository root, using the Python environment you already use for LAYA:

```bash
python -B experiments/batch_v2/experiments/requested-action-500/run_experiment.py
```

You can also open that file in your IDE and press Run. It checks the input hashes, makes seven small interface probes using the existing fruit example, runs the complete comparison, then prints a development-only report named `research-development/START-HERE.md`. There are no cases/suite/mode/rule-mode arguments to assemble. `--dry-run` validates and prints counts without loading a model.

Every normal launch creates a new run folder. An interrupted run can be resumed using the existing runner command printed by the launcher. After a successful resume, rebuild the safe first report with `run_experiment.py --report-run PATH_TO_RUN_FOLDER`.

If the SDK rejects any requested temperature, the launcher stops before the large run and preserves probe evidence. We will explicitly revise the suite; it never silently substitutes a different temperature. A successful request does not prove what numeric temperature the SDK internally used.

## What runs

| Item | First round |
| --- | --- |
| Fixed inputs | 500: 420 settled, 80 unsettled; 125 scenario families |
| Question/choice variants | 10, all with the same three labels and their order |
| Native rules | 10, including the current rule and an ungated reference |
| Temperature settings | SDK default, 0.5, 1, 1.5, 2, 3, 5 |
| Model inference calls | 35,000, plus 7 setup probes |
| Rule outcomes | 350,000 |
| Rule mode | Replay: each model response is evaluated by all ten rules |

The original runner still writes raw responses and separate question/rule/configuration folders. At this size, checkpoint and report writing can take significant time even when model calls are fast. The initial campaign report avoids the full all-pairs bootstrap; uncertainty is computed for candidate comparisons before pruning in the next step. No runtime estimate is promised.

## What to send back

Open **the printed `research-development/START-HERE.md`**, then bring that file and its companion `screening.json` back for analysis. Keep the entire run folder for exact evidence and later calibration. `results/` is ignored by Git, so merging the experiment does not upload your results. Share the small development report first; the shared handbook describes exporting the full evidence for a durable handoff.

Do not choose settings from the runner's overall report: it includes the held-out cases. We select question wording from development cases, temperature from the temperature subset, rules from the policy subset, and evaluate the frozen finalists on held-out cases once.

## What happens next

We keep the baseline and plausible alternatives, refine temperature around the promising tested regions, then compare how many requests each rule answers and how often those accepted answers are wrong. DOCTOR is an additional offline comparator using the saved probabilities. All later rounds reuse the exact same `cases.json`. No result is promoted to production automatically.

- [Exact task and input-agent instructions](task-definition.md)
- [First-round experiment and decision plan](rounds/001-broad.md)
- [Dataset counts and limitations](dataset-summary.md)
- [Annotation review](annotation-review.md)
- [Preparation checks and remaining live verification](preparation-checks.md)
- [Run journal](run-journal.md)
- [Runnable suite](../../../experiments/requested-action-500/rounds/001-broad/suite.json)

500 is a useful first stress benchmark, not proof of representative traffic or a rare-error guarantee. The final held-out comparison has 84 settled cases from 21 families; small differences may remain unresolved.
