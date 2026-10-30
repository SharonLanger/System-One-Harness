# Call-navigation helpers — future work only

Neither helper is implemented or connected to a flow/hook in this change.
The current change only removes formatter-added Markdown and makes paths
relative to the hook event cwd. Content, notes, rules and size warnings stay the
same. Future helpers return navigation data for a later building block.

## Contracts

`get_called_method_locations`: given a file and callable ID, return the project
methods called from its implementation, with definition locations and call sites.
Reuse the existing `listCalledCallables` resolution implementation. It already
scans nested callback bodies and excludes definitions contained inside the
selected method. Add source locations through a new operation; preserve the old
operation's response, whose Python validator enforces an exact set of fields.

`get_calling_method_locations`: given a file and callable ID, find invocation
sites targeting that callable throughout an explicitly selected project. Return
the enclosing caller's definition range and every call-site span. This requires
project-wide discovery, not just following the target file's imports.

Both take `path`, `callable_id`, `repository_root`, and `cwd`. Caller lookup also
takes an explicit tsconfig path. IDs come from the existing outline; reject stale
IDs. Code text alone is insufficient for semantic resolution. Relative input
paths resolve from cwd. Canonical absolute paths remain internal; returned IDs
remain opaque snapshot identifiers. Returned navigation paths are relative to
cwd, including `../` for siblings.
The working directory is a display/input base, not the repository boundary.

Definition line numbers are one-based and end lines inclusive. Call-site spans
use one-based lines and UTF-16 columns, with an inclusive start position and an
exclusive end position. If a span ends at column 1 of the following line, retain
that position; the following line contains no characters of that call. This
distinguishes two invocations on the same line. Definition ranges cover the
complete implementation; they can be used to request source later. Neither
operation returns method bodies by default.

## Input/output examples

These names, locations and IDs are illustrative, not captured execution output.
Suppose `/repo/src/run.ts` defines `run` on lines 10–18, calls `work` on lines
12 and 15, and `/repo/src/work.ts` defines `work` on lines 3–8.

Outgoing input:

```json
{
  "path": "../src/run.ts",
  "callable_id": "<outline-id-for-run>",
  "repository_root": "/repo",
  "cwd": "/repo/tools"
}
```

Outgoing response:

```json
{
  "status": "ok",
  "data": {
    "methods": [{
      "path": "../src/work.ts",
      "callable_id": "<outline-id-for-work>",
      "name": "work",
      "signature": "export function work(): void",
      "start_line": 3,
      "end_line": 8,
      "call_sites": [
        {"path": "../src/run.ts", "start_line": 12, "start_column": 3, "end_line": 12, "end_column": 9},
        {"path": "../src/run.ts", "start_line": 15, "start_column": 3, "end_line": 15, "end_column": 9}
      ]
    }]
  },
  "diagnostics": []
}
```

Incoming input targets `../src/work.ts` and its ID, with the same root/cwd plus
`tsconfig_path: "../tsconfig.json"`. Its output uses `data.callers`: an entry
with `kind: "method"`, `path: "../src/run.ts"`, `name: "run"`, its outline ID,
definition lines 10–18, and the two call sites above. Include a `data.scope`
record naming the config, searched files, and any search limits or omissions.

A top-level invocation uses `kind: "module"`, null callable ID/name, and the
enclosing statement range. For nested callbacks, keep the actual call-site span
and use the enclosing file-outline callable where available. Never fabricate an
extractable ID for an unsupported anonymous scope. One target/caller is returned
once with all its distinct call sites. Order by path and source position.

## Resolution and coverage

Use TypeScript compiler symbols for imports, aliases and re-exports; names alone
are insufficient. For incoming lookup, start with the TypeScript Language Service
call-hierarchy API. The current outgoing helper uses a single-file program and
`readDirectory: () => []`; that setup cannot discover all incoming callers.
Build project membership from tsconfig and record imported files added by the
compiler, including excluded-but-imported files. Config exclusions alone do not
guarantee a file is absent from the program. Respect repository confinement.
Missing/invalid config is an explicit incoming error, not a silently narrow search.

TypeScript reference implementation:
https://github.com/microsoft/TypeScript/blob/v5.8.3/src/services/callHierarchy.ts
Verify behavior against the project's pinned compiler before implementation.

Call hierarchy gives static navigation relationships, not guaranteed runtime
dispatch. Distinguish proven direct targets from injected interfaces, overrides,
reassigned variables and dynamic access. Passing a function as a value, importing
it or mentioning it in comments does not itself count as an invocation.
Standard library calls are real calls but not repository implementation hints.
Classify library references when proven; do not infer that from name alone.

Outgoing lookup is one hop. Scan inside nested callbacks without listing their
in-block implementations as extra targets or traversing returned target bodies.
Self-recursion adds no external source hint, matching current outgoing behavior.
Incoming self-recursion can appear as an explicit call site. No result means no
proven calls within the reported scope; it is not proof the method is unused.

Return `ok`, `partial`, or `error` with structured diagnostics. `ok` means analysis
completed for the declared static scope. Unresolved/dynamic calls, unsupported
constructs, project references and exhausted budgets must report partial coverage.
Stale IDs, unreadable selected source or invalid input are errors. Never silently
truncate search results or mix source snapshots. Keep JS/TSX and multi-project
support explicit; do not promise them until implemented and verified.

## Phases and independent testing

1. Document the two new API contracts in the TypeScript README. Create failing
   contract tests for the examples before implementation. Preserve the old API.
2. Add outgoing location enrichment by sharing existing resolution logic. Add
   matching Python adapter validation. No block/flow wiring.
3. Add incoming project discovery and semantic lookup, with explicit scope,
   budgets and uncertainty. Add matching Python validation. No block/flow wiring.
4. Have an independent verifier check contracts and source navigation. Run the
   relevant TypeScript/Python regression suites before a later integration phase.

An independent test-planning reviewer identified these required cases:

- Same-file/imported functions; aliases, re-exports and tsconfig paths; static and
  instance methods; arrow/function initializers; object members; optional calls;
  overloads; same names in different files/classes.
- Two calls to one target, including same-line invocations; multiline call sites;
  nested callbacks; local methods; recursion; top-level calls; non-call references.
- A caller outside the target's import graph; included test files; excluded and
  excluded-but-imported files; sibling projects and project references.
- Interfaces, inheritance, reassigned values, computed calls, `.call`/`.apply`,
  constructors, tagged templates and declaration-only targets: explicit support
  or uncertainty instead of guessing runtime implementations.
- Missing files, stale IDs, parse/config failures, service errors, timeouts,
  changed source snapshots and file/search limits: honest partial/error results.
- CRLF, Unicode and end-of-line positions; nested cwd and `../`; symlinks and
  confinement; definition ranges verified against extraction by returned ID.
- Compatibility with old outgoing callers; deterministic ordering; no unintended
  invocation from hooks/flows; no source writes and no model calls.

Current presentation verification (separate from those future helpers): an
independent reviewer checked 8 formatter option combinations, 9 newline/range
cases, exact source preservation including Markdown/backticks, relative/sibling
paths, duplicate handling and input immutability. The saved inventory example
renders 1,009 characters; selected code remains 502 characters at lines 46–56.
The hook AST differs only by passing `cwd=cwd` to the formatter. No live model
or full suite was run. Existing raw-JSON/size-rejection tests still need the
previous formatter-contract update; that broader test work is deferred.
