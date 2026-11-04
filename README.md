# System One Harness

SOH is a Python prototype that asks a local LAYA model structured questions, applies named
rules, and selects TypeScript method context for a narrowly defined Claude Code
`UserPromptSubmit` hook. The TypeScript parser is a separate Node helper. This
repository is under active experimentation; real Laya runs happen on an Apple
Silicon Mac, while most automated tests use mocks.

## Requirements

- Python 3.11 or newer.
- Node.js and npm for the TypeScript source helper.
- For **real model experiments**: an Apple Silicon Mac with a working
  `laya_mlx` and MLX Python environment and access to the configured model
  checkpoint. Installing this project's Python package does not install the
  Laya runtime or download model weights.

## Set up from a fresh checkout

Run these commands at the repository root. Generated Python and TypeScript build files live in root `build/`. The installer creates `build/python` automatically; wheels and source archives can be written to `build/packages` using `python -m pip wheel --no-deps -w build/packages .` and `python setup.py sdist --dist-dir build/packages`. Use the Python environment that
contains `laya_mlx` if you plan to run real experiments.

```bash
python -m pip install -e '.[test]'
npm --prefix typescript-helper ci
npm --prefix typescript-helper run build
```

The npm build creates `build/typescript/cli.js` and links its local npm dependencies. File and method flows
need this file: without it, they return `extractor_error`. Build once per fresh
checkout and rebuild after changes to `typescript-helper/src/`; you do not need
to build before every experiment. If you already have its npm dependencies,
run just `npm --prefix typescript-helper run build`.

The canonical CLI is `system-one-harness` or `python -m cli`. The transitional `laya-context-router` executable alias remains in the new distribution for existing hook settings. A fresh environment should install only `system-one-harness`; when upgrading an existing environment, record the old interpreter and revision first, uninstall the old distribution, then install this revision with that same interpreter. Both distributions must not own the alias simultaneously. `LAYA_CONTEXT_ROUTER_CLI` remains the plugin setting and may point to either executable from the new distribution. See [plugin setup](plugins/README.md).

To try the offline example (mock Laya, real TypeScript parsing):

```bash
PYTHONPATH=src python examples/file_method_context.py
```

To try the connected project with **real Laya** on the configured Mac:

```bash
python experiments/flow_connected_project.py
```

For a direct real Laya call without the TypeScript helper, run
`python experiments/laya_choice.py`. Experiment scripts can also be launched
directly in an IDE with the right Python interpreter selected. See
[experiments/README.md](experiments/README.md) for every script, its input,
model/temperature overrides, and saved report format.

## What the flow does

The current file-method flow recognizes a request such as:

```text
Explain `src/service.ts`: how does calculate work?
```

It detects and resolves one production `.ts` file, lists its callable signatures,
asks Laya which method is relevant, and collects that method's exact code plus
bounded dependency context. A question block loads its question definitions and
rules from JSON, prepares dynamic method choices, interprets the model response,
and enriches prediction fields for rule decisions. The result is either context
or a reasoned `noop`. Dependency coverage is partial; see reported gaps.

The hook adapter in `hooks/user_prompt_submit.py` is opt-in. It is **not
installed or activated** by setup or experiments. For the hook contract and a
future manual setup recipe, see [docs/hook-usage.md](docs/hook-usage.md).

## Read results and debug

Experiments write a timestamped `summary.md` and `details.json` under
`experiments/results/<script-name>/`. They print a summary and the saved path.
The JSON includes intermediate question and response data when the run reaches
those steps.

All layers append diagnostic events to `logs/debug.jsonl`. To investigate
`extractor_error`, search that file for `"component": "extractor"` and
`"level": "ERROR"`; the original exception and TypeScript helper output are
logged. Each experiment report records its PID, which helps associate events
with a run. `logs/` and `experiments/results/` are ignored by Git; logs may
contain prompts, responses, or source code.

## Tests and documentation

These checks use mocks for Laya and do not prove live model compatibility:

```bash
npm --prefix typescript-helper test
python -m pytest -q
```

- [Requested-action block](src/building_blocks/questions/requested_action/README.md): C1 short choices, temperature 1.0 by default, and gap ≥ 0.10. See the [500-case results and selected profile](docs/requested-action/requested-action-500-results.md).
- [TypeScript utility contracts](typescript-helper/README.md): detection, path resolution,
  signature-only outlines, exact extraction, called-callable navigation and context collection.
- Supporting utility implementation evidence (historical material; see docs/cleanup-local-files.md): test-first changes and validation.
- [Experiment guide](experiments/README.md): runnable scripts, inputs, reports,
  model settings, and diagnostic logs.
- [Mac live setup](docs/real-laya-mac.md): explicit first real-model probe.
- [Configuration conventions](docs/configuration-conventions.md): question and
  policy JSON formats.
- Implementation plan (historical material; see docs/cleanup-local-files.md) and
  progress (historical material; see docs/cleanup-local-files.md): phases, scope, and current evidence.
- [Method selection block](src/building_blocks/questions/method_selection/README.md):
  dynamic choices and acceptance rules.
- Previous README (historical material; see docs/cleanup-local-files.md): full earlier technical description,
  retained verbatim for review.

For source-level details, start with `src/` (Python flow,
questions, rules, logging), `typescript-helper/` (TypeScript AST helper),
`experiments/` (manual real-model entry points), and `hooks/` (Claude hook
adapter).


## Shared hook gateway

The public entry is `python -m hooks.gateway --hook UserPromptSubmit`. The gateway and shared contracts live together in `src/hooks/` as `gateway.py` and `contracts.py`. It reads one JSON event from stdin and validates the supplied event name against `--hook`. Common ingestion calls the UserPromptSubmit dispatcher, which calls the prompt-context enrichment handler. Unsupported events return empty stdout without model work.

For an installed development checkout, replay a saved event explicitly:

```bash
python -m hooks.gateway --hook UserPromptSubmit --repository-root /absolute/project --config /absolute/run-config.json --real < event.json
```

Project root comes from the existing explicit configuration option. Event cwd is retained as metadata; root mode resolves source references and displays paths relative to the configured root. No root is guessed from cwd. `--real` is required to enable the model.

Context returns one `hookSpecificOutput` JSON object. Normal no-op returns zero stdout bytes and exit0; handled errors also remain nonblocking but log an explicit error outcome. Diagnostics use stderr. Logs include invocation/session IDs, reason/code and output byte counts; replay captures exact stdout independently. See [hook usage](docs/hook-usage.md) and phase evidence (historical material; see docs/cleanup-local-files.md).

`hooks/user_prompt_submit.py` remains a forwarding compatibility launcher. The plugin in `plugins/hook-laya/` is configuration only and calls the gateway directly using your configured Python interpreter. Users install this repository into that interpreter's environment and choose how to enable the plugin.

See [manual plugin setup](plugins/hook-laya/README.md) for Sharon's preferred copy-to-`.claude/my-plugins` and `env.CLAUDE_CODE_PLUGIN_DIRS` recipe, plus alternative loading. No installer script, automatic copying, settings edits or activation is provided.

For each hook, the gateway reads Claude's process environment `CLAUDE_PROJECT_DIR` and adds a nullable `derived.project_dir` to the internal envelope. Original event cwd and explicit feature source root remain separate. See project-context verification (historical material; see docs/cleanup-local-files.md) for the user-run two-session test and worktree limitations.


## Optional strict input budgets

Existing `predict()` calls remain compatible and unchecked. Select `predict_strict()` for loaded-tokenizer inspection before inference, or `strict=True` on supported blocks (including ticket triage and requested action). Method-selection V2 and flows keep their existing APIs. See [strict migration](docs/token-budget-migration.md) for supported APIs, typed refusals and limitations, and [manual tokenizer smoke cases](experiments/tokenizer_smoke/README.md) for user-run local-model checks. Unit tests use mocks; real tokenizer/runtime parity remains unverified.


## Repository hygiene and assistant context

Campaign definitions, cases and campaign documentation remain versioned under `experiments/batch_v2/`. Historical feature planning notes live locally under ignored `docs/local/`. See [local backup and pull instructions](docs/cleanup-local-files.md) before updating an existing checkout.

Do not automatically open or load raw results, exports, diagnostic logs or historical docs into assistant context. Read a specific run/log only when the requested task needs it. Use maintained campaign summaries for orientation. Put generated exports under `experiments/exports/` and analysis output under `experiments/reports/`; keep raw results locally until analysis is finished.

Experiment-dependent checks are preserved but deferred under [tests/deferred](tests/deferred/README.md). The ordinary test command runs active production tests; skipped scenarios are not claimed as passing coverage. Phase two will redesign those checks.

Run `python scripts/check_repository_hygiene.py` before committing. Optional local hook setup: `git config core.hooksPath .githooks` (review existing hook configuration first). GitHub's Repository hygiene check must be made required in the main branch rules. Ignore rules prevent ordinary additions; forced adds and hook bypass remain possible.
