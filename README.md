# Laya Context Router

A Python prototype that asks a local Laya model structured questions, applies named
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

Run these commands at the repository root. Use the Python environment that
contains `laya_mlx` if you plan to run real experiments.

```bash
python -m pip install -e '.[test]'
npm --prefix typescript-helper ci
npm --prefix typescript-helper run build
```

The npm build creates `typescript-helper/dist/cli.js`. File and method flows
need this file: without it, they return `extractor_error`. Build once per fresh
checkout and rebuild after changes to `typescript-helper/src/`; you do not need
to build before every experiment. If you already have its npm dependencies,
run just `npm --prefix typescript-helper run build`.

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

- [TypeScript utility contracts](typescript-helper/README.md): detection, path resolution,
  signature-only outlines, exact extraction, called-callable navigation and context collection.
- [Supporting utility implementation evidence](docs/supporting-utilities-results.md): test-first changes and validation.
- [Experiment guide](experiments/README.md): runnable scripts, inputs, reports,
  model settings, and diagnostic logs.
- [Mac live setup](docs/real-laya-mac.md): explicit first real-model probe.
- [Configuration conventions](docs/configuration-conventions.md): question and
  policy JSON formats.
- [Implementation plan](docs/implementation-plan.md) and
  [progress](docs/progress.md): phases, scope, and current evidence.
- [Method selection block](src/laya_context_router/building_blocks/questions/method_selection/README.md):
  dynamic choices and acceptance rules.
- [Previous README](docs/README-backup.md): full earlier technical description,
  retained verbatim for review.

For source-level details, start with `src/laya_context_router/` (Python flow,
questions, rules, logging), `typescript-helper/` (TypeScript AST helper),
`experiments/` (manual real-model entry points), and `hooks/` (Claude hook
adapter).


## Shared hook gateway

The public entry is `python -m laya_context_router.hook_gateway --hook UserPromptSubmit`. It reads one JSON event from stdin and validates the supplied event name against `--hook`. Common ingestion calls the UserPromptSubmit dispatcher, which calls the prompt-context enrichment handler. Unsupported events return empty stdout without model work.

For an installed development checkout, replay a saved event explicitly:

```bash
python -m laya_context_router.hook_gateway --hook UserPromptSubmit --repository-root /absolute/project --config /absolute/run-config.json --real < event.json
```

Project root comes from the existing explicit configuration option. Event cwd is retained as metadata; root mode resolves source references and displays paths relative to the configured root. No root is guessed from cwd. `--real` is required to enable the model.

Context returns one `hookSpecificOutput` JSON object. Normal no-op returns zero stdout bytes and exit0; handled errors also remain nonblocking but log an explicit error outcome. Diagnostics use stderr. Logs include invocation/session IDs, reason/code and output byte counts; replay captures exact stdout independently. See [hook usage](docs/hook-usage.md) and [phase evidence](docs/phases/hook-gateway/progress.md).

`hooks/user_prompt_submit.py` remains a forwarding compatibility launcher with no separate input parsing or feature pipeline. Final plugin manifest/hooks JSON and preferred plugin installation instructions remain pending Sharon's supplied assets. No plugin or global hook is installed by this change.
