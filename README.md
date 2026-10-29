# Laya Context Router

Reusable Python decisions with a lazy Laya SDK boundary. Implementation is staged
in [the plan](docs/implementation-plan.md) and [progress](docs/progress.md).

```bash
python -m pip install -e '.[test]'
python -m pytest -q
PYTHONPATH=src python examples/basic_question.py
```

The example uses an explicit mock loader. No SDK, weights, GPU, service access,
or inference is required. The real adapter is implemented but has not been verified
against live Laya. Real mode is explicit and never falls back to mock success.
