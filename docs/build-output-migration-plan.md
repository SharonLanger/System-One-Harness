# Plan: collect generated build output at the repository root

Status: PLAN ONLY. No migration has been implemented by this PR.
Owner: Sol implementation agent. Escalation reviewer: Astra agent.
Reviewed baseline: `96e4278c3df95a91a1e81e4a1f7c9ed705168e66`.

## Goal and scope

Put generated project build output under `<laya-context-router>/build/`, beside
`src`, `plugins`, and `tests`. Keep the existing setuptools backend and CLI name.
Do not rename the conventional `.egg-info` suffix or manually move live metadata.
Generate it in the new location through the packaging configuration.

Target layout:

```
build/
  python/       # .egg-info and Python build intermediates
  packages/     # wheel and source-distribution output from our build command
  typescript/   # compiled TypeScript helper and generated runtime support
```

This covers repository-owned build output. Python installations and their installed
metadata/console scripts remain in the selected environment. Dependency downloads,
node_modules, model weights, logs, experiment results, __pycache__ and pytest caches
are not build artifacts to relocate in this task. External build tools can still
choose their own temporary directories or an explicitly requested output location.

Preserve hook protocol, decisions, public function signatures, package resources,
CLI arguments, model configuration, and log locations. Limit runtime edits to
helper-location/dependency-resolution plumbing required by the move. No refactor
of the gateway, dispatchers, model flow or extraction algorithms.

## Execution and escalation instructions for Sol

1. Read this plan and applicable AGENTS.md files. Fetch current main and create an
   isolated implementation branch. The local checkout used to draft this plan is
   not authoritative. Preserve concurrent changes and user work.
2. Proceed autonomously when the plan and checks succeed. Do not merge the
   implementation PR without Sharon's separate instruction.
3. If a baseline check fails, implementation check fails, assumption proves false,
   or a different design/scope is needed, call an Astra agent before deviating.
   Provide the exact failure, relevant diff, reproduction, expected behavior and
   smallest proposed correction. Ask for diagnosis and a revised plan.
4. Record Astra's advice and the chosen adjustment in the implementation evidence.
   Verify the advice with tests; do not simply treat a review as a passing result.
   Never weaken assertions or silently skip checks to obtain green results.
5. If Astra is unavailable, document the blocker and ask Sharon how to proceed.
   Continue independent checks, but do not guess a broader replacement design.

## Verified repository facts and implications

- pyproject.toml uses setuptools>=68 and src-layout discovery. There is currently
  no setup.py/setup.cfg. Its console entry point is `laya_context_router.cli:main`.
- Package data includes block JSON/Markdown and defaults/rules/questions resources.
  These must survive both wheel and source-distribution builds.
- .gitignore already ignores build/, dist/, *.egg-info/, node_modules and logs.
- TypeScript compiles CommonJS from typescript-helper/src to typescript-helper/dist.
  npm dependencies live in typescript-helper/node_modules.
- Python DEFAULT_HELPER currently resolves typescript-helper/dist/cli.js relative
  to the package's source location. Many Node tests require ../dist/*.js.
- Existing packaging tests include tests/test_cli.py, tests/test_packaged_blocks.py
  and tests/block_runtime/test_wheel.py. Inspect these before extending coverage.
- No AGENTS.md was found in the reviewed remote tree; check again at implementation.

## Phase 1: baseline and complete inventory

Search tracked code, test fixtures, scripts and docs for `dist`, `.egg-info`, build
commands, helper defaults and package-resource access. Identify executable examples
versus historical evidence; update active instructions without rewriting history.
Record current Python/setuptools/pip/Node/npm versions and relevant baseline tests.
Capture representative outline/extract output, CLI stdout/stderr and return codes.
Use mocks for model behavior; no live model or Claude session is needed here.

## Phase 2: Python packaging relocation

In a disposable clean checkout, prototype setuptools egg_info's egg_base targeting
build/python and configure build intermediates there. Do not assume that writing
an egg_base option also creates the parent directory: prove first installation
works when build/ does not exist. If configuration alone cannot bootstrap it,
consult Astra about the smallest packaging-only bootstrap before implementing it.
Avoid introducing a custom backend or changing backends without that review.

Keep explicit src package discovery if necessary so generated build directories
cannot become accidental packages. Retain all existing resource patterns and
entry points. Do not relocate installed environment metadata or the CLI launcher.

Provide one documented distribution-build command that writes wheels and sdists
to build/packages. Document any additional build-only dependency needed. Do not
claim that setuptools configuration overrides every frontend's chosen output dir.
Verify rebuilding a wheel from the generated sdist, not only from the checkout.

## Phase 3: TypeScript build relocation

Set the compiler output to the repository-root build/typescript directory. Update
Python's default helper path, Node test imports, scripts and active documentation.
Keep explicit caller-supplied helper paths working.

Moving CommonJS files changes their dependency lookup: build/typescript is not a
child of typescript-helper, so its normal lookup will not reach that node_modules.
Provide a narrowly scoped, automatically generated dependency-resolution mechanism
as part of npm run build (a build-local node_modules link is one candidate).
Prove it works from arbitrary working directories, with spaces in the checkout
path, without global NODE_PATH or globally installed TypeScript. If the candidate
fails or requires broader dependency changes, consult Astra. No manual link step
should be required of Sharon. Keep pinned dependencies/lockfile semantics intact.

Ensure missing-build messages give a runnable command from the repository root.
Do not keep a silent fallback to stale typescript-helper/dist output, which could
make verification pass with old code. Do not add unrelated wheel-bundling of the
Node helper: preserve and document the current checkout-oriented limitation.

## Phase 4: upgrade and cleanup

Simulate the old editable installation in an isolated environment first. Record
its interpreter, launcher path and metadata. Upgrade that same environment using
the migration checkout, rebuild the helper and verify it runs from outside the
repository. Compare the CLI path and protocol before/after.

After checks pass, document removal of only these obsolete generated outputs if
present: src/laya_context_router.egg-info, typescript-helper/dist, and any old root
dist output. Confirm contents are generated before deletion. Do not delete source,
logs, node_modules, Python environments or arbitrary user files. Do not implement
an automatic destructive cleanup during pip installation.

Explain that deleting build/ requires regenerating build output and may require
reinstallation of editable metadata. Test delete-and-rebuild in disposable copies.

## Required verification and acceptance criteria

- Fresh editable install from a checkout with no build/, dist/ or .egg-info works.
- Editable reinstall works; generated repository metadata lives under build/python,
  and no new src/*.egg-info appears. Git reports generated output as ignored.
- Wheel + sdist builds complete; wheel-from-sdist succeeds. Inspect archives for
  required JSON/Markdown resources and unintended generated/nested build content.
- Install a wheel in a separate clean environment, outside checkout/PYTHONPATH;
  run CLI doctor, observation and logs, and the existing packaged-resource checks.
- Editable source changes remain visible on the next process without reinstalling.
- Existing CLI, gateway/observation and packaging regressions pass. Observation
  still emits zero stdout, logs exact supplied input within existing bounds,
  and does not invoke dispatch/model work. Malformed-input behavior is preserved.
- Build the TypeScript helper from clean output; run the complete Node test suite
  and relevant Python extraction/context tests against ONLY the new helper path.
- Direct Node invocation and Python invocation work outside the checkout with
  spaces in its path and without relying on old dist files/global dependencies.
- Representative extracted code, source hashes, ranges and protocol output match
  the baseline. Explicit helper overrides and missing-build failures still work.
- Upgrade the same Python environment and confirm the CLI launcher path is stable.
- Run the complete Python suite after integration; report failures/skips honestly.
- Review the final diff: only packaging/build path plumbing, affected tests and
  documentation. No behavioral edits to model decisions or hook dispatch.

Use meaningful installation and execution tests, rather than assertions that
merely repeat config strings. Record commands, versions, outcomes and limitations
in the implementation PR. Do not claim live Mac/MLX/Claude verification from Linux.

## Sharon's manual upgrade after the implementation is approved and merged

Nothing changes from this plan-only PR. Keep using the current LCR normally.
For the actual migration, choose a quiet moment with no hooks in flight:

1. Pull the merged implementation in the LCR checkout.
2. Reinstall using the SAME interpreter previously used for LCR:
   `"/actual/python/path" -m pip install -e .`
3. Run `npm --prefix typescript-helper ci` if dependencies need installing, then
   `npm --prefix typescript-helper run build` from the repository root.
4. Run `laya-context-router doctor` and compare its launcher path with the old one.
   PATH, ~/.zshrc and LAYA_CONTEXT_ROUTER_CLI should need no changes when using
   the same interpreter/environment. Existing log location should remain the same.
5. Check observation and logs:

   ```bash
   printf '%s' '{"hook_event_name":"UserPromptSubmit","session_id":"manual-build-check","prompt":"hello"}' | laya-context-router hook --hook UserPromptSubmit --observe-only
   laya-context-router logs --last 5
   ```

   Expect no hook stdout, an observed result, and the supplied synthetic session ID.
6. Start a fresh Claude session using the existing observe-only plugin setup,
   submit a prompt and confirm a new observation. Then test one known TypeScript
   request using the previously working real-mode setup and model configuration.
7. Only after success, remove the specific obsolete generated folders listed above.

Pulling changes affects an editable install immediately, so finish the reinstall
and helper build before invoking the next real hook. The implementation agent must
supply final commands if verified mechanics differ from these planned commands.

## Rollback and handoff

Record the pre-upgrade commit. If the manual check fails, restore that version on
a clean branch/check-out, reinstall with the same interpreter, and rebuild its
original TypeScript helper before resuming. Preserve local changes and logs; never
use a blanket git clean/reset as rollback. Restore any edited plugin mode separately.

The implementation PR must include the final folder layout, exact upgrade and
cleanup commands, automated evidence, manual checks still pending, and any Astra
review decisions. This plan PR changes documentation only and authorizes no merge
or automatic changes on Sharon's computer.
