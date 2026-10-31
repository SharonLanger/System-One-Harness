# Mechanical research-tooling demonstration

Existing three fruit fixture inputs only; no new cases or research campaign. Twelve fixture inferences produce 24 logical native outcomes. These are mechanical results, not model accuracy or live capability evidence.

`compact/` contains role-filtered predictions, reproducible analysis JSON, HTML, exact definitions/roles/recipe, helper hashes and evidence inventory. `sealed/` preserves the full original raw run and its file/hash inventory. This fixture contains no held-out cases; the separation demonstrates the production handoff format. Never expose a real tuning raw archive to a tuning analyst merely because the fixture archive is public.

Reproduce from the repository root:

```bash
python -B experiments/batch_v2/checks/demo_research.py --output experiments/batch_v2/checks/output/new-demo --source-commit SOURCE_COMMIT
```

New run IDs/timestamps differ. Recompute metrics exactly from `compact/predictions.json` using `research.analyze.analyze(evidence, compact/roles.json)`. To reconstruct the original run, extract `sealed/full-raw-run.tar.gz` into a new empty directory and verify every `archive-manifest.json` inventory hash. Original frozen cases/suite references and exact byte hashes are in `compact/recipe.json`.

Durable references are recorded on the implementation branch; recipient access/checksums must be checked. Read [verification](../../../docs/track-a-verification.md) before continuing. Mac/live and browser checks remain pending; no campaign may launch from this demonstration.
