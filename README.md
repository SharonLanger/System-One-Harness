<div align="center">

# System One Harness

### Turn local Laya decisions and deterministic tools into focused Claude Code flows.

[![Offline tests](https://github.com/SharonLanger/system-one-harness/actions/workflows/offline-tests.yml/badge.svg?branch=main)](https://github.com/SharonLanger/system-one-harness/actions/workflows/offline-tests.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-2da44e)](LICENSE)
[![Experimental](https://img.shields.io/badge/status-experimental-f0ad4e)](#project-status-and-community)
[![Claude Code hook plugin](https://img.shields.io/badge/Claude%20Code-hook%20plugin-2da44e)](plugins/hook-laya/README.md)

**[Set up](#set-up-a-development-checkout)** · **[Run tests](#run-tests)** · **[How it works](#how-it-works)**

</div>

System One Harness (SOH) is a personal experiment I built for fun: a set of reusable Laya question blocks, explicit decision rules, and deterministic code tools that you can compose into Python flows. The included flow uses a local Laya model and a Node/TypeScript helper to choose relevant method context for a Claude Code `UserPromptSubmit` hook. For example, it can return context for a request such as:

```text
Explain `src/service.ts`: how does calculate work?
```

The hook emits a `hookSpecificOutput` JSON response with the selected method context, or emits no context when the request is ineligible. It does not install or enable itself in Claude Code. The project is evolving; the offline tests use scripted model responses and do not prove live model quality or compatibility with every Laya runtime.

## Build a flow

Start with one or more [question blocks](src/building_blocks/questions/) that turn model answers into typed decisions. Combine them with deterministic tools, such as the [TypeScript source helper](typescript-helper/README.md), in an ordinary [Python flow](src/flows/). The included [Claude Code hook plugin](plugins/hook-laya/README.md) shows how to expose a selected flow to Claude Code; it requires manual setup.

Before adding your own Laya question as a reusable block, test it in an experiment project. I use [System One Experiments](https://github.com/SharonLanger/system-one-experiments), a separate repository that is currently private, to try questions and rules. Bringing a successful experiment into SOH is a deliberate code change, not an automatic import.

## Requirements

- Python 3.11 or newer on macOS or Linux. The hook gateway uses POSIX timer APIs.
- Node.js and npm to build the TypeScript source helper. CI uses Node 24.
- For real inference: the [Laya-MLX runtime](https://github.com/mizorewww/laya-mlx), access to the [default Laya model](https://huggingface.co/aac6fef/laya-typed-decisions-mlx), and an Apple Silicon Mac. Installing SOH does not install Laya or download model weights. Their licenses and support terms are separate from this repository's [Apache-2.0 license](LICENSE).

## Set up a development checkout

From the repository root, in a fresh Python environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e '.[test]'
npm ci --prefix typescript-helper
npm run build --prefix typescript-helper
python -m cli doctor
```

`doctor` checks the local Python, gateway timer, and log path. It does **not** check the model, Node build, or Claude plugin. The TypeScript build creates the helper under `build/typescript/`; rebuild it after editing `typescript-helper/src/`.

To see the CLI interface without a model:

```bash
python -m cli --help
```

For real model setup and an explicit first probe, follow [the Mac guide](docs/real-laya-mac.md). To connect the hook to Claude Code, follow [the plugin setup guide](plugins/hook-laya/README.md). The installed CLI is `system-one-harness`; `laya-context-router` remains a compatibility alias. No setup command above registers the hook or modifies Claude settings.

## Run tests

After the setup above:

```bash
python -m pytest -q
npm test --prefix typescript-helper
python scripts/check_repository_hygiene.py
```

The Python suite includes unit, integration, system, and existing active tests. See [the test guide](tests/README.md) for suite boundaries and how to find each job's results on GitHub. The experiment-derived checks in `tests/deferred/` are deliberately excluded from the ordinary test command; they are retained for later migration and are not counted as passing coverage. The TypeScript tests run separately with Node. GitHub Actions runs these checks on pull requests.

## How it works

The public hook gateway reads one JSON event from stdin. It validates the hook name and event, dispatches `UserPromptSubmit` or `PostCompact`, and writes only the hook protocol response to stdout. The current prompt flow resolves one production TypeScript file, asks the model to classify the requested action and choose a callable, then extracts bounded method context. A session store suppresses repeated enrichment until compaction. Diagnostics go to stderr and `logs/debug.jsonl`; session state uses files under `logs/session-state/` for now. Logs may contain prompts, model responses, or source code, so handle them as potentially sensitive.

For the gateway contract and manual registration, see [hook usage](docs/hook-usage.md). [Configuration conventions](docs/configuration-conventions.md) explain the question and policy JSON formats. [TypeScript helper documentation](typescript-helper/README.md) covers source parsing and extraction. [Plugin documentation](plugins/README.md) describes the optional Claude Code integration.

## Project status and community

SOH is an experimental research prototype made for fun, not a stable published package or hosted service. Real inference currently requires local setup. Tests exercise the harness with controlled responses; they do not establish the model's answer quality. Some historical experiment checks remain deferred.

For bugs and changes, read [CONTRIBUTING.md](CONTRIBUTING.md). To report a vulnerability privately, read [SECURITY.md](SECURITY.md). Project-owned source is offered under [Apache License 2.0](LICENSE); separately obtained runtimes and model weights have their own terms.
