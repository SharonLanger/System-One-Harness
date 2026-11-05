# Offline test suites

Run Python tests after installing `.[test]` and building `typescript-helper`:

```sh
python -m pytest -q tests/unit
python -m pytest -q tests/integration
python -m pytest -q tests/system
python -m pytest -q
```

`unit/` tests one component with isolated collaborators. `integration/` connects
real blocks, flows, and source utilities to a scripted Laya boundary. `system/`
starts at a hook or CLI entry point and checks the resulting behavior. Tests in
each suite mirror the relevant `src/` package. Existing root-level production
tests remain active while their coverage is moved into these suites; they are
included in the full run.

`support/` contains a scripted Laya fake, an in-memory session store, and a
recording logger. Production still uses the file session store and JSONL logger.
Use temporary directories for tests of actual file persistence or process
boundaries. Do not use experiment modules or generated reports as test inputs.

The deferred experiment checks remain excluded by `pyproject.toml`. Each
relevant harness scenario needs an active replacement before removing a deferred
case; experiment reporting and export behavior belong to the experiment project.

The first migrated cases are file resolution, file-reference detection, and
answer rules under `unit/`. Existing first-flow tests and a new real
prompt-to-context chain are under `integration/flows/`. Prompt, duplicate
suppression, compaction, and session isolation are under `system/hooks/`.
