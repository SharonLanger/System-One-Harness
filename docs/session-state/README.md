# Session state store

`SessionStateStore` saves raw events and loads a session's history. Import it directly from `typescript-helper/src/session-state.ts` in TypeScript, or `build/typescript/session-state.js` after building. It has no model dependencies and does not import the TypeScript compiler.

```ts
import {SessionStateStore} from '../../typescript-helper/src/session-state';

// Both arguments come from the caller's runtime configuration/payload.
const state = new SessionStateStore('/absolute/path/to/lcr/logs', sessionId);

// Hook caller example. Hook integration is a later increment.
await state.save({
  source: {kind: 'hook', name: 'UserPromptSubmit'},
  type: 'UserPromptSubmit',
  payload: {},
});

// Flow caller example, after producing successful enrichment.
await state.save({
  source: {kind: 'flow', name: 'method-enrichment'},
  type: 'context_enriched',
  payload: {files: [{filePath: '/project/src/cart.ts', methodNames: ['calculateTotal']}]},
});

const events = await state.load();
const count = events.filter(event => event.type === 'context_enriched').length;
```

Files live at `<logsRoot>/session-state/<sessionId>.jsonl`. The caller must supply an absolute log root and a session ID containing only ASCII letters, digits, `_`, or `-`. A missing log loads as `[]`; the first save creates it. Existing empty files also work. All writes append; there is no update/delete API. Missing fields and unsupported JSON data reject before writing.

Each line records `source`, `type`, `payload`, and a UTC ISO `timestamp` assigned when save is called. Loads return file order. Event types are open strings. Full prompt text and code are not required.

One shared instance serializes its operations. Input is captured before queueing and results do not alias caller data. Share one instance per session; separate instances/processes are not coordinated. Before hooking up the Python runtime, decide writer ownership and bridging explicitly. No hook or flow is wired in this increment.

Before appending, the store validates existing history. A valid final record without LF receives a separator LF before the next event, preserving all old bytes. Corrupt history, including invalid UTF-8, rejects with the path and line number. Read/write failures propagate; no automatic retries, repairs, or truncation occur. Each save reads the full history, so cost grows with log size; this is intentional for the initial small logs. A successful append does not guarantee survival across power loss. The log directory is assumed to be application-owned; this class does not defend against external symlink manipulation.

Run offline validation from the repository root:

```sh
npm --prefix typescript-helper ci
npm --prefix typescript-helper run build
node --test typescript-helper/test/session-state.test.cjs
npm --prefix typescript-helper test
```

Tests use temporary files and injected filesystem failures, with no Claude, LAYA, or tokenizer calls. Existing `logs/` ignore rules cover generated session files.

Hook event naming: source.kind is hook; source.name and type preserve the exact hook name (PostCompact, UserPromptSubmit). Flow action types use snake_case, such as context_enriched. Existing historical records are never rewritten.
