# Method selection 200

Implementation of [the expanded experiment plan](plan.md). The campaign uses 200 explanation requests, two method-question wordings, the ten unchanged rules from requested-action-500/versions/1/suite.json, and temperatures 0.5, 0.8, 1.0, 1.1. The multiple-method guard remains fixed. The campaign preserves frozen experimental settings. The subsequent [V2 adoption report](../../../../../src/laya_context_router/building_blocks/questions/method_selection_v2/research/method-selection-200-results.md) documents the selected production default and development evidence.

## Run from the repository root

```bash
python experiments/batch_v2/experiments/method-selection-200/run_experiment.py --validate-only
python experiments/batch_v2/experiments/method-selection-200/run_experiment.py --dry-run
```

No arguments also runs validation/dry-run. Expected: 200 cases, 80 vectors, 1,600 inference attempts and 16,000 logical outcomes. These commands do not load a model. Outlines are frozen inline; rebuilding TypeScript is unnecessary for execution. Reauthoring fixtures requires the standard TypeScript helper build.

On the configured Apple Silicon Mac with the intended model already cached:

```bash
python experiments/batch_v2/experiments/method-selection-200/run_experiment.py --smoke --mode live
python experiments/batch_v2/experiments/method-selection-200/run_experiment.py --mode live
```

Smoke: eight calls, 80 outcomes, separate folder marked smoke. Main: 1,600 calls, replay only. Install nothing automatically. Inspect smoke payloads, observed settings, and truncation before running main. Choose optional `--max-seconds` and `--worker-timeout` limits from smoke timing. Failed attempts consume the budget. Resume with `--resume <run-folder>`; it reuses frozen settings and evidence.

The main launcher automatically generates development reports. Regenerate without inference:

```bash
python experiments/batch_v2/experiments/method-selection-200/summarize_results.py --run <run-folder> --split development
```

Add `--allow-partial` for labelled partial reports. Output is `analysis/development/`: four temperature CSV/Markdown pairs, two question CSV/Markdown pairs with four temperature tables each, vectors, raw-answer summaries, totals, reasons and a hashed report manifest. Rates use exact summed counts, never averages of percentages. Pooled counts describe repeated experimental outcomes, not independent requests or a production ensemble.

Before held-out/all summaries, create the plan's frozen-finalists JSON with run/cases/suite hashes, baseline IDs, up to two finalist vectors, freeze timestamp and SHA-256 of the development vectors.csv. Pass `--finalists <file>` and the requested split. The script validates the guard before loading held-out evidence.

## Evidence and boundaries

Canonical raw responses are stored once in eight question/temperature JSON partitions, at most 200 records each in this campaign, indexed by inference ID. Atomic partition replacement permits resume without duplicate raw checkpoints. Case checkpoints retain both rule decisions and final source ID. The attempt ledger counts actual calls separately from replay outcomes.

The dataset covers 140 selectable cases and 60 refusals; 100 semantic operation/domain families remain intact across the 120/80 development/held-out split. See [dataset summary](dataset-summary.md) and [annotation review](annotation-review.md). Annotation has author self-review only; independent review is still outstanding. Do not present this benchmark as independently reviewed or representative production traffic.
