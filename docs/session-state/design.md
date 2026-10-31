# LAYA session state: minimal first increment

Status: first storage increment implemented; hook integration and flow policies remain later increments.
Date: 2026-10-31

## Goal

Provide one TypeScript class that saves raw events to a session JSONL file and loads them back. Flows and the hook dispatcher can use the same API. The class owns file access; callers own event meaning and decisions.

This increment has two public operations: `save` and `load`. There is no repository/service split, query language, update operation, delete operation, compaction policy, or enrichment limit built into storage.

## Implementation steps

1. Define the event types and the two-method contract below. Add contract and validation tests.
2. Implement session path validation, directory/file creation on first save, and append-only saving. Test exact persisted lines and preservation of prior bytes.
3. Implement loading in file order, including empty/missing files and clear error handling. Test round trips and malformed input.
4. Add focused examples for hook and flow callers and document the supported writer model. Run the relevant tests and type checking.

Each step should be a small, testable commit. Inspect the current repository before choosing source/test locations and reuse its filesystem, validation, and test utilities where suitable. Do not change experiments, model execution, tokenizers, existing flow behavior, or unrelated tests. This document proposes the contract; it does not claim those repository utilities have already been inspected.

## Storage location

`<logsRoot>/session-state/<sessionId>.jsonl`

The intended `logsRoot` is one explicitly resolved `logs/` directory belonging to LCR's runtime configuration. Callers must reuse that same absolute location, rather than resolve it from whichever working directory a hook happens to receive. Selecting its concrete runtime anchor belongs to integration.

All sessions share the `session-state` folder. Every session has exactly one file named with its session ID. The class is bound to one session at construction. Session ID is not duplicated in every line.

The first `save` creates missing directories and the session file, then appends its first record. There is no header or synthetic initialization event. An empty file is valid. `load` on an absent file returns `[]` without creating it. This avoids adding a third public initialization method.

Runtime log files should be excluded from version control when integrated.

## Data structure

```ts
type JsonValue =
  | null
  | boolean
  | number
  | string
  | JsonValue[]
  | { [key: string]: JsonValue };

type EventSource = {
  kind: 'hook' | 'flow';
  name: string;
};

interface SessionEventInput {
  source: EventSource;
  type: string;
  payload: { [key: string]: JsonValue };
}

interface SessionEvent extends SessionEventInput {
  timestamp: string;
}
```

- `timestamp`: UTC ISO timestamp assigned by the store during saving. It records logging time, not proof of when the underlying action completed.
- `source.kind`: identifies a hook event or a flow event.
- `source.name`: hook name or stable flow name supplied by the caller.
- `type`: event name supplied by the caller, such as `prompt_submitted`, `context_enriched`, or `compaction_completed`.
- `payload`: plain JSON properties describing the event. Use `{}` when none are needed.

Keep source and type separate: a flow can produce multiple event types without encoding its identity into every type string. Storage does not maintain a registry of allowed hook names, flow names, or event types.

For enrichment, use a `files` array so one event can describe one or several files. Each entry has `filePath` and `methodNames`. Callers should supply consistently resolved absolute file paths; storage preserves those strings without reading the source files or resolving symlinks.

Example physical JSONL lines (illustrative flow name):

```jsonl
{"timestamp":"2026-10-31T18:00:00.000Z","source":{"kind":"hook","name":"UserPromptSubmit"},"type":"prompt_submitted","payload":{}}
{"timestamp":"2026-10-31T18:00:00.050Z","source":{"kind":"flow","name":"method-enrichment"},"type":"context_enriched","payload":{"files":[{"filePath":"/project/src/cart.ts","methodNames":["calculateTotal"]}]}}
```

The compaction event name is only a future caller convention. This design does not assert which Claude hook proves compaction has completed. Verify that separately before wiring it.

Full prompts, source code, generated enrichment text, event IDs, schema versions, and prompt correlation IDs are not required in this increment.

## Class interface

```ts
interface SessionStateAccess {
  save(event: SessionEventInput): Promise<SessionEvent>;
  load(): Promise<SessionEvent[]>;
}

declare class SessionStateStore implements SessionStateAccess {
  constructor(logsRoot: string, sessionId: string);
  save(event: SessionEventInput): Promise<SessionEvent>;
  load(): Promise<SessionEvent[]>;
}
```

The interface describes the contract; a separate abstraction hierarchy or dependency-injection framework is unnecessary.

### Save

1. Validate input and create a timestamped event.
2. Serialize immediately into a string, so later caller mutations cannot change queued output.
3. Ensure the directory exists.
4. Append the serialized event plus one newline using UTF-8 and append mode.
5. Resolve with the saved event only after the append succeeds.

No read-modify-write cycle. Never replace, truncate, sort, deduplicate, or modify existing records. Calling `save` twice intentionally produces two records. Do not automatically retry an ambiguous write failure, because that can duplicate an event.

### Load

Read and parse the session file, returning events in physical line order. Missing or empty file means `[]`. Do not sort by timestamp: two records can have equal timestamps, and clocks can move backward.

The trailing newline is a separator, not an extra record. Accept LF and CRLF line endings and a valid final JSON record without a trailing newline. Reject unexpected blank records and malformed JSON with a useful error containing the file path and line number. Validate the basic event shape while loading; preserve unfamiliar event type names and JSON payload fields.

Do not silently skip broken records or return `[]` for permissions, parse, or I/O errors. That could make later flow logic mistake damaged history for a new session. Do not repair or truncate the file automatically. A partial record caused by interruption remains an explicit error for now.

### Extracting information

Callers use normal array operations after loading:

```ts
const events = await state.load();
const enrichmentCount = events.filter(
  event => event.source.kind === 'flow'
    && event.source.name === 'method-enrichment'
    && event.type === 'context_enriched'
).length;
```

Payload-specific queries require the caller to validate/narrow the payload structure. Storage exposes no `count`, `findLast`, `hasEnrichedFile`, or SQL-like method in this increment.

## Basic safeguards

- Use `JSON.stringify(event) + '\n'`; never interpolate JSON by hand or pretty-print records. Embedded newlines, carriage returns, tabs, quotes, backslashes, and control characters must round-trip without producing additional records. Preserve Unicode, including Hebrew.
- Accept plain JSON data only. Reject cycles, undefined properties, functions, symbols, bigint, non-finite numbers, and non-plain objects instead of silently losing or transforming data. Use existing validation utilities if available.
- Validate `sessionId` as a non-empty filename-safe token, proposed pattern `^[A-Za-z0-9_-]+$`. Reject rather than sanitize invalid IDs. In particular, reject separators, dots, traversal, and control characters. Confirm the actual session IDs fit this contract during integration.
- File paths inside payloads are data; never execute them or use them to select the session log destination.
- Serialize operations through one store instance per session in a process. A tiny internal promise queue is sufficient; a rejected operation must not permanently poison later operations. `load` on that instance waits for earlier saves.
- This first increment does not promise safe overlapping writes from separate processes or separate store instances. Before live hook wiring, verify the writer lifecycle and add coordination if overlapping processes can write the same session. Do not assume one append call makes all cross-process behavior safe.
- Successful saving means the filesystem write completed; power-loss durability and automatic crash recovery are outside this increment.

## Focused test cases

Use temporary directories and synthetic events. No live model, tokenizer, or Claude process is needed.

1. First save creates the expected folder and session file with exactly one complete JSON line.
2. Subsequent saves preserve all prior bytes and append records in order.
3. Missing and zero-byte files load as `[]`; loading a missing file creates nothing.
4. Two session IDs remain isolated; a fresh instance can load earlier saved history.
5. Quotes, slashes, backslashes, embedded LF/CR/tab/control characters, Hebrew, and emoji round-trip without extra records.
6. One enrichment event preserves multiple files and method names.
7. Empty payloads and unfamiliar event names survive round trips.
8. Invalid event shapes and non-JSON values fail before append; prior content stays intact.
9. Invalid session IDs cannot escape the session directory or alias another filename through sanitization.
10. Malformed JSON, invalid stored shapes, blank interior records, and partial trailing records report the correct line; nothing is rewritten.
11. Valid final records without a newline and CRLF files load correctly.
12. Permission and write errors reject rather than report success or empty state.
13. Concurrent calls on the same instance preserve complete records and invocation order; loads wait for earlier saves; a failed queued operation does not block all future calls.
14. Mutating input after calling save cannot alter the serialized record; the returned event matches its persisted contents.
15. Equal timestamps do not change file order; saving an identical input twice produces two records.

## Later increments, discussed separately

Wire selected hooks and successful enrichment events through this class. Verify the actual session ID, shared log-root location, cross-process behavior, error handling at the hook boundary, and the correct completed-compaction signal before enabling that wiring.

Then add the first flow's decision: enrich a file once since the latest completed compaction. Other flows can choose their own limits. Those are caller policies and do not require a second storage layer now.

The current PR implements the agreed storage increment. Additional stateful features can be discussed and added to that same PR before merging. This design does not authorize an automatic merge.

## Implementation decisions from Astra review

The runtime is Python, but this increment implements the approved TypeScript contract in `typescript-helper/src/session-state.ts`. Tests import the compiled standalone module directly; it does not load the compiler-heavy extraction entry point. Bridging Python hooks is deferred to integration.

Astra identified that blindly appending to an otherwise valid JSON record without a final newline would corrupt the file. Save therefore reads and validates the entire existing history before append, then adds a separator LF only when needed. No existing bytes are rewritten. Corrupt history causes save to reject without appending. This adds O(history size) validation per save, accepted for the first small logs.

Implementation files: `typescript-helper/src/session-state.ts`, `typescript-helper/test/session-state.test.cjs`, and `docs/session-state/README.md`. The existing `logs/` ignore rule already covers runtime files.

Astra approved the read-validate-append refinement and identified two validation gaps during code review. Regression tests demonstrated both failures before correction: invalid UTF-8 was replaced during decoding, and a sparse array with a numeric non-index property could serialize with data loss. The store now uses fatal UTF-8 decoding with file/line errors and rejects invalid array indices and array subclasses.
