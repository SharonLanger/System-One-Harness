# Formatter and call navigation — detailed test plan

Status: implementation and tests are in progress. Case IDs below specify acceptance
requirements, not a claim that every named case has been executed or completed.
Companion contract: [call-navigation-plan.md](call-navigation-plan.md).

## Test organization and evidence

- Python `tests/test_context_format.py`: pure presentation and project-root validation.
- Existing `tests/test_prompt_hook.py`: protocol, root wiring, logs and warning boundaries.
- Existing `tests/test_hook_scenarios.py`: real extraction with a mock model boundary.
- New TypeScript outgoing/incoming navigation suites, using the repository's existing test runner and layout: real compiler and real source fixtures.
- Python adapter tests alongside existing TypeScript adapter tests: strict schema validation plus actual helper subprocess integration.
- Reporting tests alongside existing experiment reporting tests: exact emitted payload visibility.

Use small checked-in source fixtures or temporary project trees. Expected source
slices and spans must be independently specified, not calculated by the helper
being tested. Derive snapshot IDs using the public outline API, then verify returned
IDs can extract the expected declaration. Do not hardcode machine paths, PIDs,
timestamps or incidental model probabilities. Each test asserts useful behavior,
not just that no exception occurred. Record targeted red/green output per phase;
existing correct behavior needs regression coverage, not an artificial red run.

## A. Previous formatter commit: durable regression tests

Each numbered item is a separate test or a parameterized family.

- F01: minimal valid context produces plain labels, path, inclusive line range and exact selected code.
- F02: no formatter-added Markdown headings, bullet notes or fences; assert on formatter boundaries, not all source characters.
- F03: source containing headings, backticks, template strings and triple-backtick comments remains byte-for-byte unchanged as a string.
- F04: imports, declarations and notes switches: all eight boolean combinations; each section appears only when enabled and nonempty.
- F05: an import is controlled by include_imports independently of other declarations.
- F06: dependency with the selected source range is omitted as a duplicate.
- F07: duplicate dependency path/range appears once; same name in different files remains distinct.
- F08: separate ranges in one file remain separate even if source strings are identical.
- F09: enclosing class dependency remains intact; do not strip matching method text from valid source.
- F10: known gap categories map to their documented readable notes; parameterize every mapping.
- F11: repeated gap categories deduplicate notes while keeping stable order.
- F12: unknown gap messages yield the generic note; raw diagnostics, hashes and internal AST fields do not leak into presentation.
- F13: hashes or diagnostic-like words inside actual source remain unchanged; filtering must not edit code.
- F14: no dependencies/no gaps produces no empty section labels.
- F15: deep-copy comparison before/after formatting proves input immutability; repeat formatting yields identical text.
- F16: single-line implementation, with and without terminal newline, has the correct inclusive last line.
- F17: multiline source uses LF, CRLF, CR, U+2028 or U+2029; parameterize terminal newline present/absent.
- F18: multiple trailing blank lines retain their exact source and appropriate occupied-line range.
- F19: Unicode/emoji before or within implementation does not change line counts or source text.
- F20: selected method, imports and supporting declarations each retain their own file and start line.
- F21: saved inventory-shaped fixture displays method lines 46–56 and interface lines 9–12 with exact fixture source. Avoid asserting a total character count that changes with the path base.
- F22: formatting performs no source reads, model calls, extraction or response enrichment; it uses the validated object supplied.

## B. Project-root behavior: tests must fail before the new change

- R01: explicit absolute project_root maps `/repo/src/a.ts` to `src/a.ts`.
- R02: run from root, a nested directory and an unrelated directory; identical input/root gives identical output.
- R03: change hook event cwd while stable configured root stays constant; displayed paths do not change.
- R04: hook repository/install directory differs from analyzed project; paths use the analyzed project's root.
- R05: selected source, dependencies, imports, call sites, searched-file scope and config paths all use the same root base.
- R06: relative source/config inputs resolve from project_root, regardless of process cwd.
- R07: absolute in-project input and equivalent relative input identify the same source.
- R08: root with trailing separator and normalized dot segments gives identical output; spaces and Unicode in directory names survive.
- R09: missing, empty, relative, nonexistent or non-directory root is rejected clearly; hook logs a safe no-op and never silently falls back to cwd.
- R10: prefix collision `/repo` versus `/repo-other` does not establish containment.
- R11: `..` escaping root and symlink escaping root cannot produce a normal in-project navigation target.
- R12: symlink aliases inside the root follow a documented canonical identity policy and do not duplicate targets.
- R13: external library target is classified separately; no fake relative project file is returned.
- R14: raw extractor canonical paths and IDs are not rewritten by presentation.
- R15: root is supplied once through existing configuration or a documented explicit option; mock/spying boundary verifies it reaches the formatter and helpers unchanged.
- R16: fixture copies in two absolute directories produce the same display paths; IDs may differ by snapshot and are not assumed portable.

Root validation belongs at the public boundary; avoid filesystem validation in a
pure formatter if an upstream validated root contract already guarantees it.
The formatter must require that root rather than use an implicit cwd fallback.

## C. Hook and experiment regressions for previous changes

- H01: accepted selection emits exactly one valid UserPromptSubmit protocol object whose additionalContext is the formatter's exact text.
- H02: stdout contains only the protocol; model progress, diagnostics and logs cannot contaminate it.
- H03: no-op emits no context and logs its reason; do not confuse empty stdout with literal JSON null.
- H04: prepared and emitted records contain exactly the actual payload; emission is logged only after successful output write.
- H05: output write failure cannot produce a successful response_emitted record.
- H06: formatted context lengths threshold minus one, exactly threshold and plus one: all are sent intact; warning only for greater than threshold.
- H07: threshold 8000 is the default; larger positive thresholds remain valid; zero/negative/invalid values retain explicit validation.
- H08: large internal raw metadata but small rendered context does not trigger a context-size warning.
- H09: oversized method source is sent unchanged with warning; no truncation or silent omission of support.
- H10: Unicode context uses the documented character-count unit, not UTF-8 byte length.
- H11: warning logs include actual count, threshold and send-unchanged action, without altering flow decisions.
- H12: model/parse/extractor exceptions retain existing safe no-op and failure logs.
- H13: model call count, rule application, answer enrichment and selected method are unchanged by formatting/root changes.
- H14: summary shows exact returned protocol plus unescaped additionalContext; details retain the same payload.
- H15: summary on no-op clearly states no context was sent; prepared-only content must never be labeled sent.
- H16: terminal summary, saved summary, details and trace agree on the current run; historical trace lines cannot become current output.
- H17: class methods, arrow initializers and anonymous/default extraction fixtures still preserve exact selected implementation in the protocol.
- H18: input size ceilings, deadlines, invalid JSON and duplicate JSON keys keep their existing guards; output warning policy does not disable them.

### Existing assertion migration

Inspect current tests before editing. Preserve unrelated assertions in each test.

- `test_full_context_metadata_counts_towards_budget`: replace obsolete raw-metadata budget expectation with H08.
- `test_context_character_budget_no_truncation`: retain no-truncation coverage, replace output rejection with H06/H09.
- `test_duplicate_json_and_oversize_context_fail_closed`: split independent input-JSON rejection from output-size warning; preserve the former.
- `test_context_invalid_budget_before_sdk`: remove obsolete rejection of 8001, add valid-positive acceptance without weakening invalid-value checks.
- Tests asserting HEADER plus serialized collector JSON: assert protocol and exact plain presentation, plus absence of internal metadata outside source.
- `test_class_method_full_hook_source_and_complete_render_budget`: retain class source assertions and update only the approved output-budget behavior.
- Any cwd-specific presentation expectation becomes explicit project-root behavior. Keep cwd handling tests unrelated to display semantics.

## D. Outgoing calls: real TypeScript fixtures

- O01: same-file named function resolves to its implementation path, signature and definition lines.
- O02: imported named/default/namespace function resolves to its implementation; parameterize forms.
- O03: renamed imports, barrel re-exports and tsconfig path aliases resolve by symbol, not text name.
- O04: same name in different files/classes returns only the actually resolved target.
- O05: static class and statically resolvable instance method calls return their proper class-qualified names.
- O06: file-level arrow/function initializers and object method implementations resolve or report an explicit unsupported diagnostic.
- O07: two calls to one method produce one target with two sites; identical-line calls retain distinct columns.
- O08: call inside an inline callback to an outside helper is included; callback implementation is not a target entry.
- O09: nested local function calls to outside code are scanned; local definitions inside selected method are not external target entries.
- O10: self-recursion adds no external outgoing source hint.
- O11: one-hop only: A calls B and B calls C; querying A returns B, not C.
- O12: overload call maps to implementation range, not just an overload declaration; declaration-only target is diagnosed.
- O13: optional invocation with a statically known symbol resolves without claiming it always executes.
- O14: no calls returns an empty successful list for the reported scope.
- O15: standard library calls are classified as external/library; a project function named Map is not classified by name alone.
- O16: function passed as argument, imported or mentioned in comments/string text is not an invocation.
- O17: dynamic computed access, mutable function variable and interface-dispatched call do not fabricate a concrete runtime implementation.
- O18: inheritance/overrides distinguish static declaration resolution from uncertain runtime dispatch.
- O19: constructors, tagged templates, `.call`, `.apply` and bound functions each have a named test asserting supported navigation or an explicit limitation; no silent omission presented as complete.
- O20: deterministic output ordering by path/source position and distinct site deduplication.

## E. Incoming calls: real configured-project fixtures

- I01: same-file and cross-file callers return enclosing implementation ranges and exact invocation spans.
- I02: caller not reachable through target's imports is found by configured project discovery.
- I03: alias/default/namespace/barrel/path-mapped imports resolve to the same target without name-only false positives.
- I04: unrelated same-name functions and methods are excluded.
- I05: multiple sites in one caller aggregate; different callers remain separate.
- I06: callback-contained call is attributed to enclosing supported outline method, preserving actual site span.
- I07: module-level call returns kind module, null callable ID/name and enclosing statement range.
- I08: self-recursion appears as an incoming invocation site.
- I09: import, export, assignment, function-as-value and comment-only references are excluded.
- I10: configured test callers are included; callers outside declared project scope are not silently included.
- I11: excluded-but-imported file entering the TypeScript program is reflected in searched scope and results.
- I12: excluded and unreferenced file stays outside reported scope.
- I13: sibling project/project references produce explicit bounded coverage or diagnostic; no claim of whole-monorepo completeness.
- I14: invalid/missing tsconfig yields error rather than a single-file fallback pretending to be full coverage.
- I15: no callers means none found in reported static scope, not unused everywhere.
- I16: function-value escapes/dynamic dispatch yield uncertainty where detected, never invented callers.
- I17: overloaded/static/instance/arrow callables have extractable enclosing caller IDs where supported.
- I18: unsupported anonymous caller scope retains honest location/diagnostic without manufacturing an outline ID.

## F. Shared locations, errors and compatibility

- S01: returned definition ranges extract the exact expected implementation by returned ID.
- S02: LF/CRLF, Unicode before a call and multiline invocations obey one-based UTF-16 columns and exclusive site ends.
- S03: call span ending at next-line column 1 retains that endpoint; definition line range remains inclusive.
- S04: missing/unreadable source, stale IDs and malformed inputs yield explicit errors, not empty success.
- S05: source changes during analysis cannot mix snapshot locations/IDs; retry or explicit error according to documented policy.
- S06: parse errors affecting resolution are diagnosed; no silently reliable-looking incomplete results.
- S07: timeout, file count, byte and result budgets yield bounded partial coverage with explicit omitted scope; no silent truncation.
- S08: compiler/language-service failure maps to a structured error without stdout protocol corruption.
- S09: missing/unresolved imports preserve resolved targets plus partial diagnostics where appropriate.
- S10: Python validator rejects missing keys, wrong types, invalid statuses, impossible ranges and malformed call-site spans; parameterize each field.
- S11: Python adapter round-trips valid ok/partial/error responses from the real TypeScript helper.
- S12: old listCalledCallables response remains exactly compatible with its strict validator and existing consumers.
- S13: unsupported JS/TSX/project-reference configurations explicitly report limitations until tested support exists.
- S14: operations do not modify source/config files, instantiate Laya or invoke either helper recursively.
- S15: existing flow/hook executions never invoke the new operations; verify via the helper operation boundary.
- S16: stable order and no duplicate results across repeated runs on the same source snapshot.

## Fixture packages

1. **Presentation fixture:** selected implementation, import, interface/global declaration,
   duplicate dependencies, known/unknown gaps, internal hashes and source backticks.
2. **Small connected project:** controller → service → static utility, same-file helper,
   alias/barrel exports, duplicate names and multiple call sites. Handwritten expected ranges.
3. **Nested scopes:** callbacks/local functions, recursion, top-level calls and value references.
4. **Project discovery:** tsconfig includes/excludes, imported excluded file, unrelated caller,
   optional sibling project and path mapping. Scope expectations specified per fixture.
5. **Uncertainty:** interface dispatch, mutable references, computed calls, package declarations,
   missing modules and syntax failures. Expected errors/partial results specified explicitly.
6. **Path/range fixture:** nested process directories, Unicode/spaces, symlinks where supported,
   LF/CRLF variants and same-line calls. Platform-specific skips require stated reasons.

## Completion checklist

- Every numbered case maps to committed test names, or an explicit justified deferred support case.
- Unsupported syntax must still have an honest diagnostic test; deferring support is not silent omission.
- Project-root tests fail against old behavior for the intended reason before implementation.
- Outgoing/incoming tests fail because the new contract is absent, not because a fixture is malformed.
- Previous presentation behavior gains persistent tests; historical ad hoc checks are not counted as them.
- All relevant TypeScript/Python suites run after each implementation phase; results/skips recorded.
- Independent reviewer checks source ranges, API compatibility, root wiring and absence of new flow integration.
- Automated verification uses no real model calls; live Mac/model validation remains a separate manual step.


## Acceptance review and deferred verification

The current tests group several case IDs into broad fixtures. Such a label does
not establish every assertion in that case or every member of a parameterized
family. The following gaps were identified during implementation review; they
remain open acceptance work, not removed requirements. Record final executed
commands/results separately from this review.

- Incoming I17 currently has an arrow target/caller fixture; overload, static and
  instance caller families still need independent range/extraction checks.
- Incoming I18 needs an unsupported anonymous-caller fixture with a diagnostic
  and no fabricated callable ID. I16 needs mutable aliases and `.call`, `.apply`
  and bound-function escapes in addition to computed access and direct value use.
- S05 requires a deterministic mutation-during-analysis test. Source comparisons
  in implementation alone are not evidence that snapshot mixing is prevented.
- S07 requires exhausted-budget fixtures. Incoming currently bounds file count
  and bytes per file; elapsed time, total bytes and result-count budgets remain
  deferred implementation work. A subprocess timeout is not a structured partial
  result and cannot satisfy this requirement by itself.
- S08 compiler/service-failure injection, S13 JS/TSX omission diagnostics, and S15
  proof at the helper-operation boundary still require explicit verification.
- S10 malformed-schema tests need the full field/type matrix, same-line distinct
  callers/targets, invalid ID ranges, and malformed searched-file members. S11
  needs real partial/error round-trips as well as successful responses.
- R10–R12 require navigation fixtures covering prefix collisions, lexical escape,
  symlink escape and canonical in-root aliases. R05 and R16 require all navigation
  path fields and relocation equivalence, not only formatter path assertions.
- H04–H05 emission-write ordering/failure and H14–H16 experiment reporting still
  require evidence tied to the actual emitted payload, including no-op and stale
  historical trace cases. Existing assertions must be inspected before crediting
  these as covered.

The incoming implementation now uses TypeScript call-hierarchy relationships
as its primary candidate set, and uses AST traversal to locate expression spans
and enclosing owners. A targeted test verifies a hierarchy-filtered relationship
does not reappear from mere symbol equality. Default compiler libraries are
available. Package type files that are omitted are surfaced in partial scope
and diagnostics. These changes address the initial review concerns but do not
complete every listed acceptance case. Unsupported JS/TSX, multi-project
traversal and indirect runtime dispatch remain deferred support; uncertainty
must be explicit whenever detected.
