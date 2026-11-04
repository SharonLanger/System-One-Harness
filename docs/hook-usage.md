# UserPromptSubmit: first method-context flow

The default hook routes through the gateway, common dispatcher and UserPromptSubmit dispatcher to `flows.first_method_context.handle_prompt`. The flow enriches explanation and test-generation prompts referring to one production TypeScript file.

It returns the complete selected method and one level of called-method navigation: project-relative path, signature and inclusive definition lines. Called-method bodies, recursive dependencies and incoming callers are not included.

## Offline verification

Build the existing TypeScript helper, then run:

```bash
python -m pytest -q tests/first_flow
```

Tests mock both public requested-action and method-selection building blocks; deterministic source utilities, dispatchers and serializer run normally. Model/tokenizer tripwires prevent real inference. These tests verify orchestration and transport, not model answer quality or actual Claude delivery.

The older `examples/user_prompt_submit_scenario.py` uses a historical SDK-only mock designed for the sandbox. It is retained unchanged and is not the current first-flow acceptance command.

## Manual registration recipe

Install the package in the selected interpreter and build the pinned helper. Replace the absolute placeholder paths and supply the configured model environment. This document does not activate hooks or modify Claude settings.

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"/absolute/system-one-harness/.venv/bin/python\" \"/absolute/system-one-harness/hooks/user_prompt_submit.py\" --repository-root \"$CLAUDE_PROJECT_DIR\" --config \"/absolute/run-config.json\" --real --deadline 10",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
```

Use a synchronous command hook. The earlier `hooks/user_prompt_submit.py` path remains a forwarding wrapper. New registrations can use `python -m hooks.gateway --hook UserPromptSubmit` with the same operational arguments.

To disable it, remove this UserPromptSubmit entry while preserving unrelated settings. Omitting `--real` produces no enrichment without loading the model. Tests exercise the recipe with public block mocks, including opt-out behavior, without installing settings.

`--deadline` defaults to 10 seconds; the outer timeout should allow additional grace. Cold model loading and live latency require separate measurements in the supported environment. Source/config lookup uses the explicitly configured absolute `--repository-root`, supplied here from `CLAUDE_PROJECT_DIR`; event/process cwd never supplies a fallback.

## Context and budgets

`--max-context-chars` lowers the first flow's hard limit of 8,000 UTF-16 code units; a larger setting cannot raise that cap. The count includes headers, source, locations, separators, notes and footer. The selected implementation is never truncated. Complete call-list entries are omitted with an explicit count when needed. If no valid complete-method representation fits, no enrichment is emitted.

The source string retains its exact formatting and line endings. The flow logs that exact final enrichment through the existing logger. Decoding its `additional_context` log field reproduces the hook's returned text. Prepared context is not proof of successful emission or Claude consumption.

Legacy dependency-depth/source-budget flags remain accepted but do not request dependency-body collection in the new flow. Tokenizer support is separate pending work and is not implemented by this flow cleanup.

## Hook protocol

Synthetic input:

```json
{"session_id":"example","transcript_path":"/repo/transcript.jsonl","cwd":"/repo","hook_event_name":"UserPromptSubmit","prompt":"Explain `src/service.ts`: how does calculate work?"}
```

Illustrative successful output:

```json
{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"Enriched Prompt for System 1\nFile: src/service.ts | Method: calculate | Lines: 1–1\nfunction calculate(x: number) { return x * 2; }\n\nMethods called by calculate:\nNo project methods were reported.\n\nContext scope: selected method only."}}
```

The original user prompt is preserved. Success emits one JSON object with `hookSpecificOutput.hookEventName` and `hookSpecificOutput.additionalContext`. No selection, unsupported action and handled errors emit zero stdout bytes and exit with the existing nonblocking behavior; diagnostics remain in logs/stderr.

The gateway validates common fields, owns final serialization and isolates ordinary Python/fd1 noise from protocol stdout. It requires session_id, transcript_path, cwd, hook_event_name and prompt for UserPromptSubmit; permission_mode is optional. Transcript contents are not read. Input `hook_event_name` and output `hookEventName` intentionally have different spelling.

## Sandbox and reusable components

The old implementation is `flows.sandbox_file_method_context`. `flows.file_method_context.run` remains a compatibility re-export for existing experiments, examples and live-check callers. The old enrichment adapter is explicitly sandbox-only and disconnected from the default dispatcher; its root/config preparation helper is still reused.

The reusable `context_format.format_context` utility and dependency collectors remain available to their existing callers. Their supporting-body format is not the active hook format. The new flow's presentation is in `flows/first_method_context.py`, and it uses the existing outgoing navigation utility.

See the design (historical material; see docs/cleanup-local-files.md), test plan (historical material; see docs/cleanup-local-files.md) and sandbox retirement (historical material; see docs/cleanup-local-files.md) for implementation scope and coverage. Live Claude delivery remains a separate check.
