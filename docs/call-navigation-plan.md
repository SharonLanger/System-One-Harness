# Call-navigation helpers — implementation contract

Implementation and regression tests are now in progress. Neither navigation
helper is connected to a flow/hook. This document remains the acceptance contract;
implementation presence does not mean every completion gate below has passed.
The previous formatter's hook-cwd behavior is historical, not the new contract.
Relative input and output paths use an explicit, stable **project root**, never
the process cwd or changing hook cwd. See the detailed test plan's acceptance
review for remaining verification and support gaps.

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

Both take `path`, `callable_id`, and `project_root`. Caller lookup also takes an
explicit tsconfig path. IDs come from the existing outline; reject stale IDs.
Code text alone is insufficient for semantic resolution. Relative input paths,
including tsconfig paths, resolve from project_root. Canonical absolute paths
remain internal; returned IDs remain opaque snapshot identifiers. All navigation
paths are project-root-relative. External targets are classified separately;
never manufacture project locations for them.

Project root must be explicit and absolute. At hook integration, use a stable
configured project root; do not guess it from process cwd, event cwd, or the helper
repository location. Inspect existing root configuration before implementation;
reuse it if it already supplies this value. If it does not, document one explicit
configuration option. Missing/invalid root produces a logged safe no-op at the
hook boundary and a validation error at the helper boundary. Establish this
wiring before changing formatter callers. Internal existing repository_root
parameters can be mapped at the adapter without a broad rename.

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
  "path": "src/run.ts",
  "callable_id": "<outline-id-for-run>",
  "project_root": "/repo"
}
```

Outgoing response:

```json
{
  "status": "ok",
  "data": {
    "methods": [{
      "path": "src/work.ts",
      "callable_id": "<outline-id-for-work>",
      "name": "work",
      "signature": "export function work(): void",
      "start_line": 3,
      "end_line": 8,
      "call_sites": [
        {"path": "src/run.ts", "start_line": 12, "start_column": 3, "end_line": 12, "end_column": 9},
        {"path": "src/run.ts", "start_line": 15, "start_column": 3, "end_line": 15, "end_column": 9}
      ]
    }]
  },
  "diagnostics": []
}
```

Incoming input targets `src/work.ts` and its ID, with the same project root plus
`tsconfig_path: "tsconfig.json"`. Its output uses `data.callers`: an entry
with `kind: "method"`, `path: "src/run.ts"`, `name: "run"`, its outline ID,
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

## Implementation phases and gates

1. **Restore durable coverage for the previous commit.** Add formatter tests for
   current plain-text behavior and hook protocol/reporting tests. Update only
   assertions made obsolete by the approved formatter and warning-only changes.
   Preserve unrelated checks. These retrospective tests may pass immediately;
   do not deliberately break correct code to manufacture a failure.
2. **Project-root contract, test first.** Add tests that fail under current cwd
   behavior, record the meaningful failure, then implement explicit root wiring.
   Cover formatter, hook, adapters and documentation. Keep source content intact.
3. **Outgoing helper, test first.** Define the new TypeScript operation/schema,
   add failing tests, reuse semantic resolution, add Python adapter validation.
   Preserve the old listCalledCallables operation and all existing consumers.
4. **Incoming helper, test first.** Add explicit configured-project discovery,
   semantic invocation lookup, honest scope/limits and adapter tests.
5. **Independent verification.** Review the diff against this contract; verify
   fixture-derived locations and recorded test results. Run all relevant Python
   and TypeScript regression suites. Resolve failures rather than weakening tests.
   Neither new operation is wired into a building block or hook in these phases.

For each phase: define expected results before implementation; run targeted tests
first; implement; rerun the targeted tests and the relevant existing suites.
Keep failure/pass evidence and report skipped tests explicitly. Do not delete
coverage because an implementation fails it. No real Laya calls are needed:
mock only the model boundary; exercise real formatting, extraction, adapters and
hook subprocesses where those are the subject of the test. Live Mac validation
is a separate later manual step, not a substitute for automated coverage.

## Detailed test specification

See [call-navigation-test-plan.md](call-navigation-test-plan.md) for named cases,
fixtures, assertions, error policies, regression migrations and completion gates.
Every case there is planned, not claimed executed. Parameterized families should
expand into independent cases, with readable failure names.

## Historical verification (not durable regression coverage)

Before this plan, an independent reviewer ran in-memory formatter checks covering
8 options combinations, newline/range cases, exact source preservation, paths,
deduplication and immutability. These were not committed tests. No full suite or
live model run validated that formatter commit. The new first phase explicitly
closes that gap; the historical cwd output is not an acceptance baseline for the
new project-root behavior.
