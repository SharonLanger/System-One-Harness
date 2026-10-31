# Results and errors

Each launch creates a new dated run folder. The counts printed at startup are the
plan, not proof that the work finished. Case files are checkpoints of completed
work; seeing some of them does not mean that the entire run completed.

## What is saved

- `inferences/`: the model request, raw answer/probabilities, timing and error,
  once per inference (shared across rules in replay mode).
- `batches/`: each case's rule decision and scoring metadata. Keep these for
  analysis and resume. The 500-case broad grid plans 35,000 inferences and
  350,000 rule outcomes, so the full results directory can still be substantial.
- `manifest.json`, `attempts.json`, `heartbeat-*.json`, `active.json` and
  `worker-*-status.json`: small execution/status records.
- `worker-<configuration>.jsonl`: errors only. No successful prediction, debug
  payload, enrichment or rule-replay traces. Each file is at most 1 MiB, with
  two rotating backups (`.1`, `.2`), at most 3 MiB per worker configuration.
  The oldest log entries expire; durable case/inference errors remain in their
  checkpoints. Error messages and stack traces in diagnostics are truncated to
  2,048 characters each. Successful workers may produce no log file.

Inference records retain an empty `logs` array for compatibility; debug logs are
no longer copied into those records. The manifest records the logging policy.
This policy is experiment-owned and changes no production source files. SDK
console warnings are separate and are not silenced by this change.

## When a run stops

Start with the small files: `manifest.json`, `attempts.json`, the
`worker-*-status.json` files, `heartbeat-*.json`, and `active.json` if present.
Keep the final PyCharm console error too. These usually establish the last active
case, attempted call count and whether a worker exited or hit a limit. A hard
process kill may leave a stale `running` manifest; it is not evidence of success.
The large worker log is not needed for the first diagnostic pass. Do not delete
the incomplete run or relaunch just to obtain a cleaner folder.

After a successful requested-action-500 run, open
`research-development/START-HERE.md` inside the dated run folder; its companion
`screening.json` contains the machine-readable development results. If these are
absent, inspect execution status first. The overall `report.html` includes all
splits, so it is not the report used to choose experimental settings.

## Existing runs

This change does not shrink, rotate or rewrite old result folders. Resume checks
the runner fingerprint and will reject an older run after this code update.
Keep the original code revision available if you need to resume that run; do not
edit its manifest to bypass the check. Diagnose the current stopped run before
deciding whether to resume with its original runner or start a fresh run.
