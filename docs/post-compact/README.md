# PostCompact logging

Build with `npm --prefix typescript-helper run build` and ensure Node is on PATH. The plugin adds `hook --hook PostCompact --log-state` and retains the existing prompt hook. Manual and automatic compaction append an exact `PostCompact` event with an empty payload and UTC timestamp under the LCR installation's `logs/session-state/<session_id>.jsonl`.

The adapter serializes writers using `logs/session-state-locks/`. Compaction summaries are omitted from session and route diagnostic logs. Hook input is capped at 1,048,576 characters. Operational errors are reported through stderr; success emits no stdout. No model or tokenizer is called.

Offline checks: build the TypeScript helper, run its test suite, and run `PYTHONPATH=src python3 -m pytest tests/test_post_compact.py`. Tests use synthetic inputs and temporary logs. The final user-run smoke test is `/compact` in a Claude version supporting PostCompact; verify exactly one added record for that session ID. See `plan.md` for the design and acceptance cases.
