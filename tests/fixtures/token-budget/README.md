# Pinned offline tokenizer qualification

Before the test suite, install `pip install -e '.[test]'` and explicitly run:

```
python scripts/prepare_token_budget_fixtures.py --download
```

For fully offline setup, use `--source /path/to/tokenizer.json` instead. Both routes verify SHA-256 before installing one shared vocabulary in `.token-budget-fixtures/`. Tests never fetch data and fail when the fixture is absent or altered. This setup is mandatory for qualification, not a skipped optional suite. No model weights are used.

`manifest.json` identifies exact checkpoint revisions, the shared vocabulary and separate configurations. `typed/` and `code/` preserve each checkpoint's original LICENSE/NOTICE. `SDK-LICENSE` preserves the Apache-2.0 license of mizorewww/laya-mlx revision `2159c6c9988e4cbfd6281db1888cef45de09cea9`. Rendering/normalization in the application adapts that runtime's rules to expose untrimmed input; it is modified code, not an upstream file. Independent SDK helpers are qualified in the next increment. No code-model neural/runtime qualification is implied.
