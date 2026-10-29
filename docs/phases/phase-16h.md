# Phase 16H — hook boundary hardening after integration handoff

Starting local candidate: `f44e7dd` (Phase 16, independently reviewed; remote
publication ID to verify). Requested handoff:
`/workspace/scratch/c0679bf67556/laya-hook-integration-handoff.md`.
Astra High reviewed the existing implementation and identified the real native
stdout gap without recommending a rewrite of correct hook behavior. Luna Medium
independently planned focused regression cases before implementation.

Scope: retain the existing additive Claude response and no-op contract. During
the synchronous flow, redirect Python and fd1-native SDK progress to stderr;
restore stdout before the one final protocol object. Preserve the internal flow
result boundary, repository-root/nested-cwd distinction and explicit live opt-in.
No SDK or Claude execution is claimed.

Tests: a fake SDK writes via `print`, `os.write(1, ...)` during load/predict and
`sys.__stdout__`, then returns a decision or raises. Before the fix, both paths
failed: native text preceded JSON or occupied a supposed no-op stdout. After the
fix, exact parsed envelope or empty stdout/exit 0 and SDK chatter on stderr.
Additional subprocess cases cover unrelated input fields, missing/ambiguous
source, complete Unicode/provenance context budget, and deadline during stdin,
load and predict. Prior fixtures and test expectations remain intact. Context
overflow deliberately yields no-op rather than partial method text.

Documentation: usage includes synthetic input/output and wrong-nesting guidance,
actual CLI arguments, interpreter choice, synchronous project-local settings,
and no-op behavior. The remaining phase plan specifies expanded context budgets
and a separate actual-Claude marker/control check in Phase 20. Normal/global
hooks are not installed.

Implementer full gate: `npm --prefix typescript-helper run build` passed;
`npm --prefix typescript-helper test` passed 6/6; `PYTHONPATH=src python -m
pytest -q` passed 352/352 in 76.24 seconds, with no skips/xfail. Independent
Luna Medium verifier inspected the complete diff/handoff, found no weakened
tests, ran `git diff f44e7dd --check`, and reran sequential build, 6/6 Node and
352/352 Python in 84.86 seconds, zero skips/xfail. Verdict: VERIFIED for this
mock-backed hook-hardening scope. This phase's native writes are simulated in a subprocess; actual
backend-native/background output and actual Claude delivery remain unverified.
