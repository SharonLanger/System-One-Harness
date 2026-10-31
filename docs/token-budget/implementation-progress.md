# Token-budget implementation progress

Implementation resumes PR #23 on `codex/token-budget-plan-20261031`; no automatic merge.
Remote base: `a3dd68f3d110799883203a681e933f4fb0a17d57` (tree `06a2bdad5c9d8650334f7589caf41197f9b4a79c`). Local snapshot `1faa2f3` has identical tracked tree; it does not supply remote ancestry. Publication commits are parented to the actual remote branch head. Current main `6295d5f` changes only experiment documentation relative to the source baseline.

## Untouched implementation baseline

Recovered fresh implementation run, after D001 setup recovery and before any feature edit: clean worktree, 441 tracked paths, exact blob/mode tree verified. Linux x86_64; Python 3.12.14, pytest 9.2.0, setuptools 84.2.1, wheel 0.48.0; Node 24.22.1, npm 11.9.0; TypeScript 5.9.3.

Commands: `python -m pip install -e '.[test]'`, `python -m pip install 'setuptools>=68' wheel`, `npm --prefix typescript-helper ci`, `npm --prefix typescript-helper run build`, `npm --prefix typescript-helper test`, `python -m pytest -q`. The recovered implementation-specific outputs (not the older planning baseline) are retained under `evidence/baseline-*`. Python: 1,209 passed, 3 existing skips, 223.81 s. TypeScript: 137 passed. Build: passed after D001. No source/test edits were present when resumed.

Live Mac neural qualification and code-model execution remain pending.

## Commit 1 — report/error contract and migration

Expected red: new test asserts `laya.budget` exists (using `find_spec` to fail an assertion, not import/setup failure). Next tests exercise JSON safety, report copy isolation, stable codes, unknown measurements, and useful exception messages. Command: `python -m pytest -q tests/test_token_budget_report.py`.

Outcome: expected red 2 assertions failed for missing capability; green `python -m pytest -q tests/test_token_budget_report.py tests/test_predict.py`: 21 passed. New module has no SDK imports or prediction side effects. Evidence: `evidence/01-{red,green}.log`. Publication SHA is recorded in the next increment (a commit cannot include its own SHA).
