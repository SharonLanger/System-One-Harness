# Token-budget plan verification and handoff

Date: 2026-10-31  
Scope: documentation only. Product source and tests were not changed.

## Planning review

The primary agent reviewed the plan against Sharon's latest requirements. Astra independently reviewed the design and execution instructions, identified corrections, and reviewed the updated plan.

The resulting plan requires:

- Sol as the implementation owner.
- A dedicated implementation PR by default; reuse of the planning PR only on Sharon's explicit instruction.
- Eleven small, dependency-ordered, green implementation commits.
- A recorded red/green TDD cycle for each new behavior, with tests committed alongside working implementation.
- Heavy real-tokenizer and independent SDK parity checks before budget accounting or enforcement.
- Preservation of existing valid inputs, loader/prediction arguments, agent identity, offline examples and mocks.
- Astra recovery for any unexpected baseline/test failure or plan mismatch, even a minor one.
- No deleted suites, weakened assertions, blanket skips/xfails, guard bypasses, silent truncation or threshold changes to manufacture green results.
- Transparent block propagation; flow-only recovery decisions.
- Explicitly pending live Mac/code-model qualification rather than a claim based on mocks.

A deliberately expected failure in a newly added focused TDD test is the only normal red step. Existing tests failing, or a different new-test failure than the one recorded, requires Astra.

## Corrections made after Astra review

1. Removed the old permission to casually update sandbox expectations. Sandbox status does not excuse a failing test.
2. Preserved dictionary/list state accepted by the direct prediction path, SDK serialization and conversation-list truncation direction.
3. Added option ordering, structured criteria, custom boolean labels, cache behavior, and tokenizer synchronization to parity qualification where existing inputs accept them.
4. Specified optional keyword-only inspection-provider wiring and ownership conflicts without changing existing loader/predict calls or AgentRegistry.get_agent return identity.
5. Moved fixture/example/wrapper capability wiring ahead of enforcement. Opaque predict-only agents require an explicit capability migration; there is no fake default fits report.
6. Required structured refusal and logging to arrive together, without duplicate generic boundary ERROR events.
7. Preserved genuine TimeoutError propagation during logging while ordinary logging failures cannot replace rejection or permit inference.
8. Required reproducible independent fixtures; absent/mismatched fixtures cannot silently skip the qualification gate.
9. Replaced six broad implementation phases with eleven testable increments and mandatory progress/deviation records.
10. Clarified planning-versus-implementation PR scope.

## Source baseline

Repository: SharonLanger/laya-context-router.  
Pinned implementation base: `83211fd88d10e4c0854797dec47df33ce8d04ea5`.

The baseline used a reconstructed source snapshot, not a Git checkout of that commit. All **438 tracked files** were verified against their repository Git blob hashes. Local Git metadata/index for exactly those paths was then created to satisfy an existing test that calls git ls-files. Source and tests remained unchanged; the worktree-to-index diff was empty after setup/recovery.

Environment:

- Linux x86_64, Python 3.12.14.
- Node 24.22.1; npm 11.9.0.
- pytest 9.2.0.
- setuptools 84.2.1 and wheel 0.48.0 for the repository's no-build-isolation packaging tests.
- TypeScript 5.9.3 from the committed lockfile.
- No real MLX/LAYA model inference and no model-weight download.

Setup used an isolated virtual environment, editable installation of the repository's test extra, npm ci, and the TypeScript build. The exact setup equivalents are `python -m pip install -e '.[test]'`, `python -m pip install 'setuptools>=68' wheel`, `npm --prefix typescript-helper ci`, and `npm --prefix typescript-helper run build`.

## Astra-directed baseline recovery

The first Python run was incomplete/non-green: it exited with status 1 after progress for 369 of 1,212 collected cases, without a normal summary. It is not counted as a completed baseline. Its unexplained early exit is kept separate from the confirmed packaging environment issue.

Three failures were identified from collection order and progress:

- tests/block_runtime/test_wheel.py::test_new_catalog_and_mocked_block_execute_from_isolated_wheel
- tests/test_cli.py::test_installed_console_command_uses_selected_environment
- tests/test_context_scope_integration.py::test_C40_installed_wheel_resources_and_execution

A focused reproduction confirmed missing setuptools in the isolated environment; the wheel build could not import setuptools.build_meta. Astra prescribed installation of the declared build requirement plus wheel, local Git index setup, rerunning these three tests, then a complete unbuffered verbose suite. No source fixes, test removals or assertion changes were authorized or made.

The three focused packaging cases passed after environment recovery: **3 passed in 13.02 seconds**.

The final full-suite command was `python -u -m pytest -vv -o faulthandler_timeout=60`. A normal completed summary and exit status are required below; partial progress is insufficient.

## Verification results

| Check | Result |
|---|---|
| Tracked-file snapshot hashes | 438/438 match the pinned source |
| TypeScript build | Passed |
| TypeScript suite | 137 passed; 0 failed/skipped; 5.225 seconds; exit 0 |
| Three packaging recovery cases | 3 passed; 13.02 seconds; exit 0 |
| Final full Python suite | 1,209 passed; 3 pre-existing skips; 226.33 seconds; exit 0 |
| Source/test diff after verification | Empty |
| Plan requirements review | All 12 checked handoff requirements present |
| Astra review | Technical corrections and recovery protocol incorporated |

The three skips were already present in the repository: two duplicate-configuration-key rejection cases in test_configuration_duplicates_deferred.py, and the source-replacement/symlink case in test_file_method_context_deferred.py. No new skips were introduced and no skipped behavior is claimed verified.

During verification, main advanced to `6295d5fc90700006cab4d61761888606b652a107` through PR #22. That commit changed only the experiment handbook Markdown documents. The test baseline remains explicitly tied to `83211fd88d10e4c0854797dec47df33ce8d04ea5`; no claim is made that it tested later executable changes.

## Limits of this verification

These checks establish the current repository baseline in the recorded environment and the completeness of this documentation handoff. They do not test an implemented token guard: none was added.

The research report records the earlier actual-tokenizer/SDK-construction experiments. Those are separate evidence and must be reproduced as implementation acceptance coverage.

Live Mac runtime identity, neural execution, the code-model backend, and full plugin delivery remain unverified. Sol must rerun the untouched baseline at its actual implementation base; this planning result cannot replace a fresh baseline.

If the fresh implementation baseline fails, follow Astra recovery before starting feature work.

## How to use this PR

Read [design-plan.md](design-plan.md) first, then [research-results.md](research-results.md). The design's section 12 is Sol's execution contract and commit ledger. This file records the planning review and baseline, including the environment recovery.

The planning PR has three documentation commits:

1. Research and tokenizer evidence.
2. Design, eleven implementation increments, and Sol/Astra instructions.
3. This verification and recovery record.

No automatic merge or feature implementation was performed.
