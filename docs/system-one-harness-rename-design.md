# PR 1 design — System One Harness naming and flat Python source

## Goal and scope

Rename current product surfaces to **System One Harness** (SOH) and move the contents of `src/laya_context_router/` directly under `src/`, while preserving runtime behavior. Deliver one independently reviewable PR. This document is an implementation plan; no refactor or live validation has happened yet.

The user explicitly rejected a replacement `src/lcr/` or `src/soh/` wrapper. Use top-level packages under the existing source directory. Do not rename the upstream LAYA model, its SDK, model identifiers or the `laya` Python package merely because the product is renamed.

Include active consumers in the same PR: tests, examples, sanity scripts and batch code must import/invoke the new production layout even though their own locations remain unchanged. Update current README instructions and links. Do not bulk-edit historical design documents, journals, research output or prior experiment evidence.

Out of scope: GitHub repository rename (Sharon owns it), experiment folder moves, batch redesign, utility extraction, transcript lookup implementation, deletion of old flows, model/rule changes, and changes to session-state semantics. The grouped follow-up handover defines their order.

## Grounding and inventory

Initial audit base: `SharonLanger/laya-context-router` main at `9c4d4da6550b9a7a881c3c3f0ec52d96b8b2605b`. Refresh the base at implementation time and inspect any intervening changes, especially open/merged session-state work. Never overwrite a newer file using this snapshot.

The audited source has packages `answers`, `block_runtime`, `building_blocks`, `cli`, `defaults` (resource directory), `flows`, `hooks`, `laya`, and `questions`. Standalone files include `blocks.py`, `context_format.py`, `json_utils.py`, `live_check.py`, `log_utils.py`, and the former root `__init__.py`.

The current distribution/command is `laya-context-router`; the command points to `laya_context_router.cli:main`. Bundled resources are keyed under the old root in pyproject. `Catalog` uses `importlib.resources.files('laya_context_router').joinpath('defaults')`. CLI and runtime modules use package-relative imports across the old root. These all require explicit migration.

## Naming and compatibility contract

Use the three-word name **System One Harness** everywhere in written product naming. Use **SOH** when abbreviated and `system-one-harness` for the distribution/command slug. Do not use the numeral 1 in new product names, filenames or identifiers. The companion handover currently retains its original filename; its naming instructions are superseded by this contract until it is updated.

| Surface | Target / treatment |
| --- | --- |
| Display name and current production README titles | System One Harness |
| Abbreviation in current usage guidance | SOH |
| Python distribution and canonical executable | `system-one-harness` |
| Canonical module entry point | `python -m cli` |
| Python source root | `src/`, with its packages directly beneath it |
| Existing `laya-context-router` executable | Transitional entry-point alias in the **new** distribution to the same `cli:main`; verify it works in a clean install and never require the old Python package |
| Existing `python -m laya_context_router.cli` and old imports | Migrate all in-repository consumers; no old wrapper package is retained |
| GitHub owner/repository URLs | Keep working existing URLs until Sharon renames the repository |
| LAYA SDK/model names and model checkpoints | Unchanged |
| Existing plugin identity, environment keys, state/log locations | Preserve compatibility, including `LAYA_CONTEXT_ROUTER_CLI`; document that it may point to the new executable or retained alias |

The display-name change does not authorize changing wire formats, event source names, persisted JSON keys, session IDs, protocol labels, or existing settings files. Inventory these separately and retain their values. New user-facing instructions use SOH while explaining any retained legacy environment key accurately.

Changing the distribution name may leave the old distribution installed. Document a clean-environment install path and a deliberate upgrade procedure; avoid two distributions owning the same console command. Do not uninstall packages or mutate the user's environment during design work.

The alias is a concrete compatibility measure for current hook configuration, but a renamed distribution does not upgrade/remove an already installed old distribution. Test the two entry points in a clean environment; document removal of the prior distribution before installing the renamed one into an existing environment. Do not claim an in-place install is safe while both distributions own `laya-context-router`.

## Source migration

1. Move each package and standalone implementation module unchanged first, then repair imports in the same coherent commit. Do not create `src/__init__.py` as a replacement root package.
2. Review the old root `__init__.py` exports. Map each supported export to its actual owning package/module and update every caller. Do not silently discard useful public functions or invent a new umbrella package.
3. Convert cross-package relative imports to absolute imports: e.g. `from ..answers.rules` becomes `from answers.rules`. Keep valid intra-package relative imports. Check all leading-dot depths; simply deleting `laya_context_router.` strings is insufficient.
4. Update dynamic module strings (`importlib.import_module`), mocks/monkeypatch dotted targets, subprocess `-m` calls, CLI entry points, code embedded in tests and generated launch commands.
5. Keep existing standalone modules at `src/<name>.py` for this PR. Shared-utility extraction is a later PR so it does not obscure the namespace change.

## Explicit packaging and resources

- Set setuptools package discovery to `src` explicitly, restricted to the intended top-level package families. Do not rely on multi-package auto-discovery or accidentally package tests/experiments/build output.
- Explicitly include standalone `py-modules`: `blocks`, `context_format`, `json_utils`, `live_check`, and `log_utils` (adjust only if fresh inventory proves a different set). The former root `__init__.py` is not a standalone module and must not become `src/__init__.py`.
- Make resource ownership explicit. A small `defaults/__init__.py` is acceptable to make `defaults` an importable resource package; resolve catalog data with `files('defaults')`. Preserve the same JSON/Markdown bytes.
- Re-key package-data declarations to the owning packages: building-block question JSON/Markdown (and any required nested resources), default question/rule JSON and README, runtime documentation as currently shipped. Inventory existing wheel contents before finalizing globs; do not omit resources that currently ship or accidentally add historical output.
- Replace old-root resource lookups with the owning package, never with CWD-dependent paths. Ensure `building_blocks` dynamic block discovery still resolves resources and executable wrappers.
- Prove importability, catalog resources and CLI behavior using a built wheel in an isolated environment outside the checkout with no source-path leakage. The TypeScript bridge currently finds `build/typescript/cli.js` by walking to a checkout root; an isolated wheel does not itself demonstrate a bundled helper or full bridge functionality. Test that integration separately in the supported checkout/build mode and make any promised standalone distribution mode an explicit packaging decision.

## Filesystem and external helper paths

- Inventory each `Path(__file__).resolve().parents[N]`, `parent`, path join, `sys.path` insertion, environment fallback and subprocess working directory before changing it. Record old resolved purpose and new resolved purpose, not just a numeric decrement.
- In a source checkout, `building_blocks/typescript.py` uses old `parents[3]` → new `parents[2]` for `build/typescript/cli.js`; `hooks/session_state.py` uses old `parents[3]` → new `parents[2]` for the repository root; and `log_utils.py` uses old `parents[2]` → new `parents[1]` for `logs/debug.jsonl`. Verify their explicit overrides and installation behavior; these arithmetic changes alone do not give an installed wheel a repository root. Package-relative resources should use resource APIs. Experiment files have not moved in PR 1, so their repository-root arithmetic must not be changed indiscriminately.
- Preserve resolution of `typescript-helper`, its built artifacts, project registries and existing session log locations. Build the TypeScript helper before tests that require it; do not change its logic or package identity as cosmetic work.
- Existing install modes may rely on a checkout-relative helper. Test supported modes as they actually exist; do not claim a standalone wheel includes the TypeScript runtime if it does not.
- Verify import ownership from repository root, unrelated working directory, editable installation and wheel installation. Flat names such as `cli`, `hooks`, `laya`, `blocks` and `defaults` require checks against accidental local shadowing.
- Root `hooks/user_prompt_submit.py` currently imports the gateway. Migrate its import if retained. The root `hooks/` directory is not by itself proof of a collision: when it has no `__init__.py`, it contributes a namespace portion and a regular `src/hooks/` package can win discovery even when the root appears earlier on `sys.path`. Confirm the actual `hooks.__file__` and gateway import origin for module, script and wheel invocations. Resolve a demonstrated conflict narrowly; otherwise leave shim removal to the planned cleanup.

## Plugin, CLI, and documentation

- Keep hook behavior and JSON output unchanged: UserPromptSubmit and PostCompact still reach the same dispatcher/flow. Do not introduce new hooks or recovery behavior.
- Preserve external hook JSON field names, event names, persisted keys and failure codes. The `observe_only` log currently records old fully qualified Python dispatcher names as string values; inventory consumers and tests, then make those values accurately describe the new target without changing the diagnostic field schema. Do not blindly brand or preserve stale implementation-path strings.
- Current plugin commands use quoted `${LAYA_CONTEXT_ROUTER_CLI}`. Preserve working existing installations unless the reviewed design adds an explicitly tested alias/fallback. Branding alone does not justify breaking the environment contract.
- Update current product/setup README files, production package README references, plugin instructions and executable examples to System One Harness/new imports. Preserve historical research results and archived documents; links in active indexes may be updated to point to moved sources.
- Bump plugin version in its manifest and README/changelog in the same PR for any plugin edit, as the repository requires. Choose the next version relative to refreshed main and the compatibility impact, not a stale assumed version.
- Update IDE launchers, CI commands and developer scripts that invoke the old module. Keep repository URLs valid. Record intentional old-name matches (compatibility executable/environment variables, historical documents) rather than requiring a blind zero-match search.

## Incremental implementation commits

### Commit 1 — source, imports, packaging and direct consumers

Perform the source move, all cross-boundary import fixes, new package discovery/resource ownership, CLI mapping and active consumer import/module changes together. A directory-only commit is not an acceptable testable checkpoint. Include focused import/resource/wheel regression tests needed to establish the new contract. Retain the current runtime behavior.

Gate: import every intended production module without loading live models; existing core unit tests; catalog and packaged-block tests; wheel contents and wheel execution from outside checkout; CLI help and offline commands; no unresolved old imports in active code.

### Commit 2 — runtime path, plugin wiring and integration

Repair/validate remaining helper lookup, subprocess, plugin/shim and working-directory assumptions; add targeted regressions only for actual path-sensitive boundaries. The source move's required path fixes and launcher import belong in Commit 1 if they are needed for its focused gates. Commit 2 adds independently coherent integration wiring and tests; never leave Commit 1 knowingly broken.

Gate: hook dispatch contract tests, session-state and TypeScript bridge tests, plugin wiring, explicit CLI override, quoted executable/repository paths with spaces, examples and batch validation/dry-run from supported launch locations.

### Commit 3 — branding, current usage guidance and release readiness

Complete current README branding and operational instructions, plugin version/changelog, migration notes and intentional legacy-name inventory. Run the full regression matrix and attach concise evidence to the PR. Tests and instructions added earlier must already be valid; this commit finishes documentation rather than deferring essential wiring.

If these boundaries cannot produce coherent green commits, combine the coupled changes instead of committing broken intermediates. Separate PRs are for independently working phases; do not split the source move from its required consumer fixes across PRs.

## Validation matrix and acceptance criteria

| Boundary | Required evidence |
| --- | --- |
| Baseline | Exact base SHA, environment/tool versions and baseline Python/TypeScript test results; list any existing failures explicitly and compare them with PR results; no live model required |
| Source imports | New top-level imports resolve to intended project files; no escaping relative imports or obsolete dynamic import strings |
| Resource loading | Catalog loads every previously available question/rule; all block resource/discovery tests retain behavior |
| Installed artifact | Fresh wheel install, no checkout/PYTHONPATH contamination; canonical command, compatibility alias, imports, catalog resources and packaged block invocation work. Record TypeScript bridge as a separate checkout/build test unless packaged support is explicitly designed |
| CWD behavior | Supported commands work from checkout and unrelated directory; explicit project/repository overrides still work |
| CLI/hooks | Existing mocked hook outputs and exit codes unchanged; stdout remains protocol-only where required |
| TypeScript integration | Existing helper build/tests and Python bridge tests pass; helper discovery still targets the intended build |
| Session state | Existing location, append/load/locking semantics and PostCompact behavior preserved; never run against user historical state |
| Experiments | Existing fixture example run, collection and resume using fresh temporary output; both real campaign launchers dry-run successfully with new production imports |
| Regression | Full configured Python suite plus batch checks and relevant TypeScript tests; report counts, new failures and baseline failures separately. Never claim full pass if baseline tests failed |
| Live acceptance | On Sharon's configured Mac, a bounded existing sanity/plugin smoke confirms actual SDK/helper invocation; label pending until observed |
| Preservation | No model/rule/default JSON content changes; no historical output contents read or rewritten; only intended source/docs/config paths affected |

Use existing test commands discovered from pyproject, package.json, CI and batch README. Expected starting commands include `python -m pytest`, `python -B -m unittest discover -s experiments/batch_v2/checks -v`, and the repository's documented TypeScript build/test commands. Do not assume dependencies, Node version or MLX are available; record missing prerequisites and use the correct supported environment.

Extend current wheel tests such as `tests/test_task_completion_wheel.py`: archive members lose the `laya_context_router/` prefix, source comparisons point at `src/`, and subprocess imports use top-level packages. Also verify private-method blocker and catalog resources. Keep behavior assertions intact.

The first PR does not move batch or sanity files; use their current paths for these checks. Later PRs use the same scenarios against the new locations. Do not rerun a costly model campaign for a namespace refactor.

## Safety critique and shared live validation

The main risks are coupled import/resource changes, stale installed entry points, and path assumptions that offline mocks cannot expose. A rename is not proof of behavioral equivalence. Keep this PR limited to naming and layout; defer cleanup, utility extraction, experiment moves and obsolete-flow deletion. Keep source moves and their required import/resource fixes atomic rather than splitting them into temporarily broken PRs.

Use one PR at a time: automated validation → Sharon reviews and merges → Sharon runs the small live acceptance checklist → agent reviews the new logs → next refactor begins. A merged PR remains **live validation pending** until this check completes. Do not start the next structural PR while a new regression is unresolved. If Sharon prefers, the same smoke checklist may also be run on the PR branch before merging.

### Before merge — agent responsibilities

- Capture the baseline SHA, installation mode and relevant existing test results. Run the automated matrix in this design once after changes; repeat only for fixes or newly identified gaps.
- Inspect current runnable entry points and choose the smallest existing live sanity commands. Provide Sharon exact copy/paste commands for the merged revision, required working directory, setup/build steps, expected output and where the newly produced logs/results will appear. Do not give guessed commands or an unbounded campaign.
- Prefer one direct-LAYA or production-block sanity and one real hook/active-flow scenario. A script that exits before inference, fixture mode, a mock example, or a deliberate missing-file scenario is not a live-LAYA check. Confirm which chosen paths actually load the model.
- Prepare an upgrade/rollback note that preserves the working environment and avoids simultaneous ownership of the legacy executable by two distributions. Record the prior working revision/plugin version. Do not casually remove Sharon's working installation to test the rename.
- Retain automated coverage for import discovery, packaged resources and persistence. Manual success supplements these checks; it does not replace them. Do not emulate Sharon's Mac or launch large campaigns simply to avoid asking him to run a short real check.

### After merge — Sharon's short checklist

1. Install/update the merged revision using the supplied steps, build the TypeScript helper if needed, and confirm the CLI resolves to that revision. Ensure the plugin's existing executable environment setting points to the intended installation.
2. Run the supplied small live LAYA/block sanity. Confirm it reaches the real model and returns a structurally valid response without import, resource or helper errors. A different stochastic model answer alone is not evidence of a refactor regression.
3. In Claude with the plugin active, submit the supplied explicit file/method prompt that exercises the active production flow. Verify the intended enrichment path and provide the new diagnostic log slice; a no-op alone does not prove the enrichment path works.
4. Submit the supplied unrelated prompt to exercise the no-enrichment path. Confirm no unwanted context or protocol output is injected.
5. Trigger manual compaction in a disposable test session to exercise PostCompact. Supply the new session-state event and diagnostic slice so the agent can verify the hook, session association, output location and absence of errors. Do not edit or reset existing session state.

Run only these bounded checks, not the full campaign matrix. If a step fails, stop there and send its command/output and relevant new logs rather than repeatedly retrying or continuing through later refactors.

### Evidence review and next-PR gate

- Sharon may upload the new logs/results or paste the relevant excerpts. Record tested revision, plugin version, commands/prompts, working directory and session identifier; inspect only the fresh evidence he supplies.
- Agent verifies the intended code path was reached, model/helper invocation occurred where required, hook output was valid, enrichment/no-op behavior matched the scenario, and PostCompact wrote the expected session event to the established location.
- Historical experiment outputs remain untouched and unread. These explicitly requested new smoke logs/results are validation evidence and may be inspected; do not overwrite prior results.
- Report each check as passed, failed or not run. Missing evidence stays pending; never treat merge, user silence or a command's zero exit status alone as proof of complete integration.
- On a regression, pause the next phase, diagnose the smallest relevant boundary and prepare a targeted fix PR or revert recommendation. Sharon controls merge/revert; repeat only affected checks plus the relevant automated tests after repair.
- After the checks pass, confirm this PR is validated and propose the next independently reviewable refactor from the handover. This explicit pause is how we avoid accumulating several unverified structural changes.

## Review, escalation and rollback

- Implementer follows this plan. Do not change flow semantics, defaults, persistence format, output schemas, or migration scope to make tests pass.
- Cheapest agent gathers a path/reference inventory without reading historical outputs. Sol verifies material findings and rejects false positives. Escalate only unresolved consequential choices to Astra with exact files, evidence, options and the user constraint.
- Stop the affected step if import collision, deployment compatibility, packaged resources or path behavior cannot be resolved within the plan. Obtain Astra's recommendation; changes to explicit user constraints still need Sharon's decision.
- Rebase/recheck against latest main before publishing. Push one review-ready PR with small commits, file-move summary, test evidence, remaining Mac validation and intentional compatibility names. Do not merge automatically.
- Rollback is reverting the PR and reinstalling the matching prior distribution/plugin in the affected environment. No state migration or historical-result rewrite is required. Do not mix old and new installed distributions.

## Follow-up boundary

The next agent must read `system1-harness-refactor-handover.md`. Production imports now originate directly in `src/`; experiment source imports must already work after PR 1. Remaining work reorganizes utilities and experiment folders, not a second Python namespace migration.
