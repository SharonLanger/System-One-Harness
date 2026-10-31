# Synthetic RV2 smoke example

From repository root:

```bash
python -B experiments/batch_v2/examples/generic-choice/run_example.py
```

IDE Play on run_example.py uses fixture mode. This makes 8 vectors, 24 outcome records and 12 synthetic inferences. The actual validators, enrichment, rules and block runtime execute; model evidence is explicitly injected. No MLX model is loaded. Open the printed report.html or comparison.md. Responses are keyed by question ID, configuration ID and case ID in responses.json; expected results are in expected-summary.json.

For live evaluation of the same input files, run:

```bash
python experiments/batch_v2/run.py --cases experiments/batch_v2/examples/generic-choice/cases.json --suite experiments/batch_v2/examples/generic-choice/suite.json --mode live --rule-mode replay
```

Live execution requires the existing Mac SDK and cached model; predictions may differ from fixtures. See ../../README.md for usage and ../../input-authoring.md for creating another experiment.
