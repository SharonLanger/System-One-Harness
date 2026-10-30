# TypeScript source utility contracts

This is the source utility API reference. The implementation uses pinned TypeScript 5.9.3, Node filesystem APIs and one JSON request/response per process; it never executes project source. Python is a transport/schema adapter. The contracts below are implemented and covered by offline tests; live Laya accuracy remains a separate Mac experiment.

| Operation | Export | CLI action | Scope |
| --- | --- | --- | --- |
| Detect references | `detectReferences(text, config?)` | `detect_references` | Configured lexical filename references; no filesystem |
| Resolve reference | `resolveReference(reference, cwd, repositoryRoot)` | `resolve_reference` | Exact paths then whole-component suffix matching |
| File outline | `outline(path)` | `outline` | Implementations outside all function bodies |
| Extract callable | `extractCallable(path, id)` | `extract` | Exact selected source only |
| List calls | `listCalledCallables(path, id, {repositoryRoot})` | `list_called_callables` | External implementation needs across the complete selected block |
| Local context | `collectLocalContext(path, id, options?)` | `collect_local_context` | Selected code and partial same-file declarations |
| Project context | `collectProjectContext(path, id, options)` | `collect_project_context` | Selected code and bounded project declaration context |

## Install, build and run

From repository root:

```sh
npm --prefix typescript-helper ci
npm --prefix typescript-helper run build
npm --prefix typescript-helper test
printf '%s\n' '{"action":"outline","path":"/repo/src/main.ts"}' | node typescript-helper/dist/cli.js
python -m pytest -q
```

Rebuild after every TypeScript change. `dist/` is generated. No C# helper, model or parser framework is required.

## Shared identity and position rules

Caller paths refer to real files. Returned source paths are canonical absolute paths. Source IDs are opaque, SHA256-snapshot-bound identities, not names; retain the full returned `id`. Editing a file invalidates its old IDs. Extraction excludes leading comments but preserves comments inside the callable, Unicode and original line endings. Ranges are zero-based UTF-16 `[start,end)` offsets; line/column are one-based UTF-16 positions. Do not slice these ranges with Python character indexing. Names/signatures are display fields; method-selection criteria use the method name as the key and signature as description. Same-name/different-signature labels use `name@line:column`; identical descriptions still abstain. `label_map` maps readable keys to IDs outside inference inputs.

Old outline/extraction/collector schemas remain version 1. New detector/resolver/call-list APIs use `{status,data,diagnostics}`: `ok` means the requested static operation completed, `partial` means useful output plus identified gaps, and `error` means no trustworthy result. Empty matches/calls are valid data; ambiguity/missing resolution has an explicit reason. CLI malformed requests or existing operation failures write stderr and exit nonzero; never treat that as a valid empty result. Python startup/deadline/JSON/schema failures raise `TypeScriptError` and existing flows may safely skip enrichment. Diagnostics are evidence of limited coverage, not proof of inconsistent source or runtime behavior.

## File outline

`outline(path)` / `outline`: request `{"action":"outline","path":"/repo/src/main.ts"}`. Returns `schema_version:1,path,source_hash,callables,diagnostics,limitations`. Each callable has `id,name,signature,start,end,location`; no body code is returned. Empty runtime files return `callables:[]`. Supported declarations include functions (async/generators/default exports), bound arrows/function expressions, instance/static methods, callable fields, object methods/properties, namespace members, constructors and get/set accessors. Signatures use the implementation source header, including binding syntax; nested callable bodies in defaults/decorators/computed names are replaced with `…`, so signatures never expose implementation code; overload signatures are excluded and the body-bearing implementation appears once. Computed names are source text and never evaluated. Interface/ambient/abstract/bodyless implementations are excluded and may be diagnosed.

Once a callable is encountered, traversal stops for that entire subtree, including parameters/defaults and body. Named local functions, callbacks and local classes/objects inside it are not peers. The private exhaustive snapshot reader is retained for exact extraction and existing collectors; it is not the public file-outline contract.

## Extract callable

`extractCallable(path,id)` / `extract`: request `{"action":"extract","path":"/repo/src/main.ts","id":"<returned-id>"}`. Response is outline provenance plus `callable,code,display_code` (no `callables` list). `code` is exact source; `display_code` separately adds line numbers. Unknown/stale ID, malformed source, missing file or unsupported selection fails explicitly; there is no name matching or full-file fallback. Extraction does not navigate calls or expand dependencies.

## Paired traversal example

```ts
function normalize(n: number) { return n + 1; }
function selected(items: number[]) {
  function inside(n: number) { return normalize(n); }
  return items.map(n => inside(n));
}
```

Outline lists only `normalize` and `selected`. Extracting `selected` retains `inside` and the callback. Listing calls from `selected` scans **all** its nested bodies, reports outside target `normalize`, omits inside target `inside`, and flags `map` when only a library declaration/no safe project implementation is available. It does not automatically scan the body of the returned `normalize` target. A self-call likewise needs no additional implementation. Containment uses canonical file and declaration ranges, never name equality.

## Detect references

`detectReferences(text,config?)` / `detect_references`: text is required, config optional. Defaults accept case-sensitive `.ts` excluding `.spec.ts`, `.test.ts`, `.d.ts`; `.tsx`, `.js` need explicit config. Include/exclude arrays contain JavaScript regex strings; exclusion wins and invalid regex/config is an input error. Capture the whole reference before filtering; preserve repeated mentions/source spelling and text spans. Quotes/backticks allow spaces; numeric line/column suffixes are not part of the path. No filesystem is read. Exact examples follow below; see [file utility tests](test/file-utilities.test.cjs).

## Resolve reference

`resolveReference(reference,cwd,repositoryRoot)` / `resolve_reference`: all inputs required; generic resolver accepts test files too. Canonical cwd-relative and root-relative exact matches are deduplicated; two exact files are ambiguous. With no exact match, search basename then match complete relative suffix components. `service1/invoice-service.ts` selects `/repo/src/service1/invoice-service.ts`, whereas basename alone is ambiguous if another service has it. `service1` never matches `oldservice1`. Absolute paths and references containing `.`/`..` navigation are exact-only. Confine real symlink targets to root, skip `.git`, `node_modules` and symlink directories; scan errors are errors. POSIX comparisons are case-sensitive. Return all ambiguous candidates, never first-match selection. This is not TypeScript import/alias resolution.

## List called callables

`listCalledCallables(path,id,{repositoryRoot})` / `list_called_callables` requires selected source path, current ID and repository root. Request:

```json
{"action":"list_called_callables","path":"/repo/src/main.ts","id":"<selected-id>","repository_root":"/repo"}
```

Response:

```json
{"status":"ok","data":{"calls":[{"path":"/repo/src/helper.ts","id":"<target-id>","name":"normalize","signature":"export function normalize(n: number): number"}]},"diagnostics":[]}
```

Results are unique by canonical path/ID and sorted deterministically. They contain no argument values or target bodies. Feed returned path/ID directly to `extract` or another call-list request. The caller owns recursion, visited set and depth limit. Imports/aliases/reexports and same-file symbols use the TypeScript checker and applicable tsconfig. Targets wholly inside the selected block are omitted while their bodies are still scanned for external calls. Dynamic indexing, injected/interface receivers, declaration-only libraries, unresolved modules and ambiguous implementations yield explicit diagnostics, not guessed implementation paths. Constructor invocations and unsupported call forms are classified. Explicit call analysis does not guarantee getter effects or runtime dispatch/execution. Invalid selected source/ID is an error.

## Local context

`collectLocalContext(path,id,{maxDepth?,maxDependencyChars?})` / `collect_local_context` request uses `max_depth` (default 2, integer 0..20) and `max_dependency_chars` (default 12000, integer 1..1000000). Example:

```json
{"action":"collect_local_context","path":"/repo/src/main.ts","id":"<id>","max_depth":2,"max_dependency_chars":12000}
```

Returns extraction fields plus `coverage:"partial",dependencies,gaps,collection`. Dependencies include `id,path,source_hash,start,end,location,kind,code,symbol_ids`; collection reports effective limits and `dependency_chars`. Empty dependencies are `[]`. Source budget counts complete dependency UTF-16 units, excludes selected code and metadata, and never truncates declarations. Supporting imports/constants/types/helpers/class state differ from called-callable navigation. Gaps include external dependencies, runtime state, closure captures, depth/size limits, class/module effects and unresolved references. Continue with supplied context while retaining the partial claim; invalid budgets or selection fail. Contract tests: `test/local-context.test.cjs`, `test/reviewed-dependencies.test.cjs`.

## Project context

`collectProjectContext(path,id,{repositoryRoot,maxDepth?,maxDependencyChars?})` / `collect_project_context`: same limits plus required `repository_root`. Example:

```json
{"action":"collect_project_context","path":"/repo/src/main.ts","id":"<id>","repository_root":"/repo","max_depth":2,"max_dependency_chars":12000}
```

Response extends local context with `project:{repository_root,config_path,config_hash,config_sources}` and gap provenance `path,source_hash`. Config fields are null when none is found; sources is a sorted array of config path/hash snapshots. Collection follows parsed Classic/Node10 resolution, aliases and supported reexports; it retains its own depth/size/source-loading limits. Missing/bad/excluded/unsupported config falls back to local partial context with an explicit gap. Modern condition-dependent resolution, separate project references, callers, automatic libraries and package implementations remain partial; `.d.ts` has no implementation. Project code/plugins are never run. Contract tests: `test/project-context.test.cjs`.

## Python bridge and logging

Use `laya_context_router.building_blocks.typescript.outline`, `extract_callable`, `collect_local_context`, `collect_project_context`; `detect_references`, `resolve_reference` and `list_called_callables` expose the new envelopes. Supply `node`, built `helper` path and positive `timeout` at most 60 seconds when needed. `DEFAULT_HELPER` targets this checkout; packaged deployments must supply a built helper with pinned TypeScript dependency. The bridge validates JSON/schema and translates transport failures to `TypeScriptError`; it does not traverse ASTs or redefine filtering. Logs append to `logs/debug.jsonl` through `log_utils` extractor events (request/startup/timeout/stderr/schema details); failed outcome envelopes log `utility_failed`. No inference is required to test these utilities.


## Copyable response and boundary examples

The following source IDs/hashes are illustrative snapshots; always use the values returned for your actual file.

### Outline and exact extraction

For `/repo/src/main.ts` containing `function selected() { return 1; }`, an outline response has this shape:

```json
{"schema_version":1,"path":"/repo/src/main.ts","source_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","callables":[{"id":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa:0:33","name":"selected","signature":"function selected()","start":0,"end":33,"location":{"line":1,"column":1}}],"diagnostics":[],"limitations":["Public outline stops at every function subtree; nested definitions and unbound anonymous expressions are excluded."]}
```

Extract the actual returned ID with:

```json
{"action":"extract","path":"/repo/src/main.ts","id":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa:0:33"}
```

The response contains the same provenance and selected metadata, plus exact code:

```json
{"schema_version":1,"path":"/repo/src/main.ts","source_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","callable":{"id":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa:0:33","name":"selected","signature":"function selected()","start":0,"end":33,"location":{"line":1,"column":1}},"code":"function selected() { return 1; }","display_code":"1: function selected() { return 1; }","diagnostics":[],"limitations":["Leading comments are excluded; inner comments and original line endings are preserved."]}
```

No supporting declarations or called-target bodies are added. Nested definitions remain within raw `code`. Ordinary/source-fidelity tests: [outline](test/outline.test.cjs), [extract](test/extract.test.cjs), [classes](test/class.test.cjs), [expressions](test/expressions.test.cjs), [public boundary and complete-block calls](test/support-contract.test.cjs). [Recursive tests](test/recursive.test.cjs) intentionally exercise the private exhaustive reader, not the public outline contract.

### Detection presets and complete paths

Production preset (also the default):

```json
{"action":"detect_references","text":"Read `src/my service.ts`:12:4 then invoice.spec.ts and again src/my-service.ts","config":{"preset":"production","include_patterns":["\\.ts$"],"exclude_patterns":["(?:\\.spec\\.ts|\\.test\\.ts|\\.d\\.ts)$"]}}
```

A shorter complete example and response:

```json
{"action":"detect_references","text":"Read a.ts and a.spec.ts and a.ts"}
```

```json
{"status":"ok","data":{"references":[{"path":"a.ts","filename":"a.ts","start":5,"end":9,"category":"production_code"},{"path":"a.ts","filename":"a.ts","start":27,"end":31,"category":"production_code"}]},"diagnostics":[]}
```

Test preset:

```json
{"action":"detect_references","text":"a.ts a.spec.ts a.test.ts a.d.ts","config":{"preset":"test"}}
```

```json
{"status":"ok","data":{"references":[{"path":"a.spec.ts","filename":"a.spec.ts","start":5,"end":14,"category":"test_code"},{"path":"a.test.ts","filename":"a.test.ts","start":15,"end":24,"category":"test_code"}]},"diagnostics":[]}
```

Each supplied include/exclude array replaces that preset's corresponding list; `include_patterns:[]` accepts none, `exclude_patterns:[]` removes exclusions. Unknown keys, non-array/non-string patterns, unknown presets or invalid JS regex return `error`, `data:null`, diagnostic `invalid_input`. Example:

```json
{"status":"error","data":null,"diagnostics":[{"code":"invalid_input","message":"Invalid detector patterns: SyntaxError: Invalid regular expression"}]}
```

Recognized filenames use POSIX paths, case-sensitive regex matching, Unicode letters/numbers and common filename punctuation. Quoted/backtick paths allow spaces. Numeric suffixes after closing quotes or unquoted filenames are locations, not path text; locations embedded inside quotes are not recognized. Backslash paths/control characters are unsupported. No normalization or deduplication occurs; spans exclude delimiters/location suffixes and use UTF-16. Categories classify accepted spellings independently of configured extensions.

Python `detect_configured_references` returns existing `FileReference` records and converts spans to Python character indices. A narrow temporary exception retains `detect_file_references(text, pattern)` as a Python-regex compatibility API, including compiled flags and conditional syntax: it classifies captures without configured filtering. Do not translate arbitrary Python regex to JS. Default flow detection uses TS with `.ts` include and no exclusions so its existing complete-mention count and production exclusion gates remain intact; explicitly provided `reference_pattern` (including the old default regex constant) uses legacy compatibility. Explicit `None` is invalid. Tests: [Python lexical compatibility](../tests/test_file_reference_utils.py), [flow gates](../tests/test_file_method_context.py).

### Exact and partial-path resolution

Given `/repo/src/service1/invoice-service.ts` and `/repo/src/service2/invoice-service.ts`:

```json
{"action":"resolve_reference","reference":"invoice-service.ts","cwd":"/repo","repository_root":"/repo"}
```

```json
{"status":"ok","data":{"resolution":"ambiguous","selected_path":null,"candidates":["/repo/src/service1/invoice-service.ts","/repo/src/service2/invoice-service.ts"]},"diagnostics":[]}
```

```json
{"action":"resolve_reference","reference":"service1/invoice-service.ts","cwd":"/repo","repository_root":"/repo"}
```

```json
{"status":"ok","data":{"resolution":"resolved","selected_path":"/repo/src/service1/invoice-service.ts","candidates":["/repo/src/service1/invoice-service.ts"]},"diagnostics":[]}
```

Completed nonselection outcomes are `missing`, `ambiguous`, `outside_repository` or `not_file`, with null selection and sorted candidates (empty except ambiguity). Input errors use `invalid_input`; filesystem/access/incomplete scan errors use `io_error`, `status:error`, `data:null`. A single plausible candidate from an incomplete scan is never returned. Root/cwd must be existing directories and cwd must be inside root. Filesystem lookup follows native casing with exact component-string suffix comparison (case-sensitive on supported POSIX hosts). Caller eligibility is separate: resolver may resolve a test file; the explanation flow checks both lexical and canonical target names to retain its production-only gate.

### Called-callable navigation outcomes

An empty successfully scanned block returns `{"status":"ok","data":{"calls":[]},"diagnostics":[]}`. With uncertain calls, useful target records are retained with partial status:

```json
{"status":"partial","data":{"calls":[{"path":"/repo/src/helper.ts","id":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa:0:33","name":"normalize","signature":"export function normalize(n: number): number"}]},"diagnostics":[{"code":"dynamic_receiver","message":"Injected or indirect receiver does not establish a concrete runtime implementation.","start":80,"end":93}]}
```

| Diagnostic | Meaning / safe continuation |
| --- | --- |
| `dynamic_receiver` | Parameter/constructor-injected, uninitialized typed field, or indirect receiver; inspect manually rather than guessing implementation |
| `dynamic_target` | Computed/indexed/IIFE invocation is unsupported; nested syntax is still scanned |
| `declaration_only` | Symbol resolves only to declarations/bodyless members; no implementation is claimed |
| `unresolved_target` | No resolvable project target (including unavailable library/package/module declarations) |
| `ambiguous_target` | More than one implementation declaration; no arbitrary choice |
| `unsupported_target` | Compiler declaration exists but cannot be extracted as a supported callable |
| `unsupported_constructor` / `unsupported_call_form` | Explicit `new` / tagged template invocation classified but not navigated |
| `missing_config` | Default Node10 resolution used; same-file targets may still be useful |
| `config_error` | Invalid tsconfig; imports are not approximated, same-file targets may remain useful |
| `stale_id` / `parse_error` / `source_error` | Error outcome with null data; refresh outline or skip source enrichment |

Call-list diagnostics use selected-source UTF-16 ranges; they never include argument values. Loading is repository-confined, root-source-only, skips package implementation directories, caps at 64 loaded sources and 4MB per foreign source; libraries are not automatically loaded. tsconfig options/aliases/extends use the compiler; project include/exclude does not prevent explicitly analyzing the selected source. Missing config is partial, not an error. Invalid config does not fall through to guessed project import settings. Read/parse failures for target sources become unresolved-target gaps. A returned implementation is navigation evidence, not proof of runtime dispatch or execution. Parameter aliases and constructor-injected fields are conservative; no data-flow engine is implemented.

### Local and project context responses

For a selection with no supporting declarations, local collection responds:

```json
{"schema_version":1,"path":"/repo/src/main.ts","source_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","callable":{"id":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa:0:33","name":"selected","signature":"function selected()","start":0,"end":33,"location":{"line":1,"column":1}},"code":"function selected() { return 1; }","display_code":"1: function selected() { return 1; }","diagnostics":[],"limitations":["Same-file semantic dependencies only; runtime state, external implementations, callers and module effects remain partial."],"coverage":"partial","dependencies":[],"gaps":[],"collection":{"max_depth":2,"max_dependency_chars":12000,"dependency_chars":0}}
```

Project collection adds project provenance and explicit caller coverage, even with no dependencies:

```json
{"schema_version":1,"path":"/repo/src/main.ts","source_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","callable":{"id":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa:0:33","name":"selected","signature":"function selected()","start":0,"end":33,"location":{"line":1,"column":1}},"code":"function selected() { return 1; }","display_code":"1: function selected() { return 1; }","diagnostics":[],"limitations":["Project coverage remains partial."],"coverage":"partial","dependencies":[],"gaps":[{"code":"caller_coverage","message":"Callers and ambient project/library context are not exhaustively analysed.","start":0,"end":33,"path":"/repo/src/main.ts","source_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}],"collection":{"max_depth":2,"max_dependency_chars":12000,"dependency_chars":0},"project":{"repository_root":"/repo","config_path":"/repo/tsconfig.json","config_hash":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","config_sources":[{"path":"/repo/tsconfig.json","source_hash":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}]}}
```

Dependency ordering is source range within the local file, and canonical path then range for project context. Dependencies deduplicate source units and retain sorted `symbol_ids`; context units can overlap selected code or other atomic declarations when syntax requires a whole statement/class. Selected code is always present even when a budget omits dependencies. The collector response remains version 1 with `coverage:"partial"` rather than the new outcome envelope. Navigate calls with `list_called_callables`; collect broader support with these operations. The limits and coverage contracts are separate.
