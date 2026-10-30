# Supporting utilities: contracts and safe implementation plan

Date: 2026-10-30
Repository: SharonLanger/laya-context-router
Reference revision inspected during this discussion: 053af28fe76d732a2a843d9f6f4d1d8a9c7c64c3
Status: design only. No implementation or tests were changed or run for this plan.

## 1. Latest decisions and scope

This plan supersedes the earlier laya-method-selection-test-first-plan.md proposal to filter only anonymous callbacks inside the Python method-selection block.

Sharon clarified that the FILE OUTLINE itself must stop at function bodies. Exclude all implementations inside those bodies, including named local functions, callbacks, nested classes and their methods. This is a general supporting-utility contract, not a special case for one experiment.

Separate the project into:
- Core mechanism: Laya loading/reuse, question definitions/preparation, enrichment, rules, interpretation, blocks and orchestration.
- Supporting utilities: detect references, resolve paths, outline source, extract one callable, list called callables, collect supporting context.

Core and support both need meaningful tests. TypeScript syntax, signature formatting, traversal, imports, symbols and call-target filtering belong in TypeScript. Python remains a thin subprocess/JSON adapter for these operations. No model is needed for supporting-utility tests.

The existing project already implements AST operations in TypeScript. Do not describe this work as rewriting a Python parser. The main changes are corrected contracts, a new call-list operation, configurable detection, suffix-aware resolution and a readable model-facing mapping.

## 2. Shared boundary

Keep the existing one-request/one-response JSON CLI and Python facade. Prefer extending it over adding another framework. An action identifies the requested operation; TypeScript owns source decisions and filtering. Node filesystem APIs handle detection/resolution support; no shell grep or source execution.

Proposed request example:
{
  "action": "list_called_callables",
  "path": "/repo/src/billing/invoice-service.ts",
  "callable_id": "<opaque-source-id>",
  "repository_root": "/repo"
}

Use the existing protocol field names where practical (the current CLI uses id); reconcile this illustrative callable_id name before freezing the contract. Do not silently change an existing action/schema. Add a new action or explicit schema version for incompatible changes.

Source identities remain opaque and snapshot-bound. Names/signatures are readable display fields. Model criteria use readable unique labels that map back to internal identities. An ID is not expected to remain valid after source edits.

Python owns process startup, deadline, JSON transport validation and translation to existing return/exception conventions. It must not implement a second AST traversal or different filtering policy. A command path and JSON boundary are sufficient preparation for another language helper later; do not implement C# or a plugin registry now.

For new APIs, use a small outcome envelope: status, data, diagnostics. Distinguish ok, partial, error; operation-specific reasons explain no matches/ambiguity. Do not migrate every existing API to the envelope in one step. Preserve compatibility wrappers during rollout.

## 3. Detector: configurable acceptance

Purpose: find references in text and accept only the configured filename types. No filesystem reads.

Proposed configuration:
{
  "include_patterns": ["\\.ts$"],
  "exclude_patterns": ["(?:\\.spec\\.ts|\\.test\\.ts|\\.d\\.ts)$"]
}

Production TypeScript is the initial preset. A test preset includes (?:\\.spec\\.ts|\\.test\\.ts)$ and excludes declaration files. The user can supply patterns to support another naming convention. .tsx, .js, declarations and additional extensions require an explicit configuration; do not silently expand the default.

Separate path recognition from acceptance: capture the entire reference first, then apply include/exclude expressions to the complete captured path. Exclusions win. Invalid regex/configuration is an input error, not an empty successful match.

Output accepted references with path, filename, text span and optional category. Preserve duplicate mentions and source spelling. Handle quotes/backticks, spaced paths and line/column suffixes deliberately; never turn invoice.spec.ts into a false invoice.ts match. Keep the default case-sensitive behavior explicit.

The filtering requirement concerns TypeScript filenames. For consistent support ownership, implement the new configured detector alongside the TypeScript helper and retain the current Python API until its callers migrate.

Implementation decision — legacy regex compatibility: retain `detect_file_references(text, pattern)` with its existing Python regex semantics, including compiled flags, named captures and conditional expressions. This is a narrow temporary exception to the thin-Python goal, already required by the compatibility rollout; do not translate arbitrary Python patterns to JavaScript or silently change this API. All new configured detection remains TypeScript-owned. Document the exception and retire it only after explicit-pattern callers migrate.

Migrate the flow's omitted-pattern path to the configured TypeScript detector through the thin Python adapter; distinguish omission from an explicitly supplied pattern with a private sentinel, preserving explicit invalid-input behavior. Explicit patterns continue through the compatibility API. Preserve the flow's lexical mention-count and excluded-file guards by configuring its TypeScript detection to include complete `.ts` references with no exclusions, then applying its existing production-only eligibility gate. Thus test/declaration mentions still count toward `multiple_files`, and a sole excluded file remains `excluded`; the standalone detector's default remains the production preset. Forward helper/node/timeout settings and handle transport failures through established flow error handling. Cover Python-specific regex compatibility, explicit versus omitted patterns, and sole/mixed excluded mentions in boundary and integration tests. This migration does not authorize weakening core eligibility or changing the configured detector's defaults.

## 4. Resolver: generic path resolution with suffix matching

Input: reference, cwd, repository_root. The resolver does not enforce production/test categories; it resolves whatever the caller supplies within the allowed repository.

Resolution order:
1. An absolute reference is exact-only and must stay inside repository_root.
2. For a relative reference, inspect cwd-relative and repository-root-relative exact candidates. Canonicalize/deduplicate; two different existing exact candidates are ambiguous.
3. If no exact candidate exists, search the repository by basename, then compare the supplied relative path as a suffix of whole path components.
4. One match resolves; zero is missing; multiple is ambiguous, with all candidates. A scan error is an error rather than a trustworthy missing result.
5. References containing explicit . or .. navigation are exact-only after normalization; do not reinterpret a failed traversal as an unrelated suffix.

Example candidates:
- /repo/src/service1/invoice-service.ts
- /repo/src/service2/invoice-service.ts

invoice-service.ts => ambiguous.
service1/invoice-service.ts => first candidate.
src/service1/invoice-service.ts => first candidate.
If /repo/legacy/service1/invoice-service.ts also exists, service1/invoice-service.ts => ambiguous.

Match path segments, not character suffixes: service1 must not match oldservice1. Search only under the repository; skip .git, node_modules and symlink directories. Resolve symlink targets before accepting them; reject paths escaping the root. Keep casing/platform rules explicit.

The suffix rule handles omitted leading directories. It does not solve misspellings, omitted middle directories, import aliases or dynamic paths. TypeScript imports use compiler module resolution, not this user-reference resolver.

Output: status, canonical selected path when unique, candidate paths when ambiguous, and diagnostics for access/I/O failures. No arbitrary first-match choice.

## 5. File outline: signatures of declarations in this file

Input: file path.
Output: readable name/qualified name, signature, opaque ID, exact range/location and source provenance. No implementation code in the outline response.

Include supported implementations declared outside function bodies:
- Standalone function declarations, including async/generators.
- Named variable-bound arrows/function expressions.
- Declared instance/static class methods and callable fields.
- Object methods and callable properties.
- Constructors and get/set accessors with distinct labels.
- Namespace members where supported.

Once a callable is identified, record its header and STOP traversing into its function subtree. This also avoids nested defaults/callbacks becoming peer candidates. Do not execute computed names, decorators, initializers or user code.

Exclude nested named functions, anonymous callbacks, local objects/classes declared inside a method body, interface-only signatures, ambient declarations and abstract/bodyless members. Do not list inherited implementations from other files as if declared here. For overloads, list the implementation once and define how its readable signature is displayed.

A class implementing an interface yields an interface-like list of its actual implemented members. It does not mean returning the interface declaration itself.

Default connected fixture must return only:
- calculateInvoiceTotal(invoice: Invoice): number
- calculateInvoiceTotalWithAdjustment(invoice: Invoice, adjustment: number): number

Both callback bodies remain present when the outer function is extracted.

Implementation note: existing internal readOutline/extraction machinery may need complete callable discovery for compatibility. Keep that private capability if needed; make the PUBLIC file-outline action satisfy the new boundary. Do not break collectors by indiscriminately deleting traversal they rely on.

## 6. Extract one callable: exact source only

Input: file path plus callable ID from an outline/call-list response.
Output: exact source string, path, identity, start/end position and line information. An optional display_code with line numbers stays separate from raw code.

No model call, call graph, dependency expansion or full-file fallback. Preserve comments inside the callable, Unicode and original line endings. Existing leading-comment exclusion should remain documented unless separately changed.

A name alone is not a safe selector: multiple classes can implement run(). Use the exact returned ID. Stale identity, invalid range, parse failure or unsupported callable must produce a specific logged error and no arbitrary source. Caller may skip and continue normal flow.

This is AST-guided source slicing, not an attempt to reproduce every behavior of Claude's Read tool.

## 7. List called callables: navigation only

Input: selected file plus callable ID and repository/project context. The helper locates the AST node; passing only a detached code string loses imports and symbol scope.

Return unique statically resolved target implementations as:
{
  "status": "ok",
  "data": {
    "calls": [
      {
        "path": "/repo/src/billing/adjustments.ts",
        "id": "<target-source-id>",
        "name": "calculateAdjustment",
        "signature": "export function calculateAdjustment(discount: number): number"
      }
    ]
  },
  "diagnostics": []
}

No argument values, full target bodies, or automatic recursive expansion in this response. Sort deterministically and deduplicate by canonical path and target ID. A caller can pass each returned path/ID to extract_callable or list_called_callables to go deeper. Any later recursive coordinator needs a visited set and depth limit.

Follow same-file symbols and imports, aliases and re-exports with TypeScript symbol/module resolution and the applicable tsconfig. Return the actual implementation file, not merely the module string or barrel file. Imports are the navigation evidence, but an import alone does not always identify the final target.

Static analysis cannot promise runtime dispatch. Interface declarations, library .d.ts definitions, dynamic indexing, injected receivers, unresolved modules, or multiple possible implementations must not be returned as a proven implementation. Report them as diagnostics with partial status when some useful targets were resolved. A malformed selected source or stale selected ID is an error.

Confirmed call-scope contract (Sharon's clarification):
The boundary is the entire selected callable's source block. Scan call sites throughout that block, including inside inline callbacks, nested named functions and nested class/object methods. Do not stop traversal at nested bodies for THIS operation.

- If the resolved target implementation is wholly inside the selected block in the same source file, it is already included: omit it from the external-call list. A self-call also needs no additional implementation.
- If the resolved implementation is outside the selected block, report its canonical file path, ID, readable name and signature. This includes another method in the same file and a method in another file.
- If a target cannot be resolved safely, flag it explicitly in diagnostics; do not silently omit it or invent a location.
- Determine containment from declaration identity, canonical source file and source ranges, never from name equality. A same-named imported or shadowed function must resolve to its actual symbol.
- This lists syntactic calls to code outside the block; it does not prove runtime execution. Even a call inside a nested function that is never invoked remains a statically observed call site.
- Do not traverse into the resolved external implementation's body automatically. The caller decides which returned targets to inspect or expand next.

Example: items.map(item => normalize(item)) inside the selected method reports normalize if its implementation is outside the block. The inline callback itself is not a separate entry. If normalize is defined inside the selected block, omit its own implementation from the list, but still inspect its body for calls to implementations outside the block. Treat map itself as a call target too: if it resolves only to a library declaration without project implementation, flag that distinction rather than pretending an implementation was found.

The outline and call-list traversal rules intentionally differ: outline stops at bodies to list declarations; call listing scans the complete selected block to discover external implementation needs. Keep the policies separate.

Explicit constructor invocations and other unsupported call forms must be classified and flagged when encountered rather than silently counted as fully resolved. Implicit runtime effects such as getter invocation are not guaranteed by explicit call-expression analysis; document that limitation.

## 8. Context collectors remain separate

collect_local_context: selected method source plus supporting declaration text from the same file. This can include relevant import statements, global/module constants, types, same-file helpers and class state declarations. It is broader than the list of calls.

collect_project_context: extends collection to project sources through imports and symbol resolution, within existing depth/size limits. Returns partial coverage and gaps.

Do not require the callers of list_called_callables to run a filename resolver to locate known targets. The helper returns canonical paths. Collectors may reuse the same symbol-resolution primitives, but retain their own content/budget contracts; do not implement them by blindly concatenating all recursively called methods.

## 9. Reuse existing APIs; avoid an unnecessary dependency migration

Research reviewed official maintainer sources:
- TypeScript Compiler API: https://github.com/microsoft/TypeScript/wiki/Using-the-Compiler-API
- ts-morph functions: https://ts-morph.com/details/functions
- ts-morph class members: https://ts-morph.com/details/classes
- ts-morph traversal controls: https://ts-morph.com/navigation/
- ts-morph imports: https://ts-morph.com/details/imports
- ts-morph signatures: https://ts-morph.com/details/signatures
- ts-morph definition/reference navigation: https://ts-morph.com/navigation/finding-references
- Maintainer alias-symbol explanation: https://github.com/dsherret/ts-morph/issues/578

These APIs provide parsing, member access, subtree skipping, declaration lookup and import navigation. ts-morph exposes class instance/static methods and getModuleSpecifierSourceFile; TypeScript's checker supplies symbols and their declarations. None removes our responsibility to define which declarations belong in this product's outline or to report ambiguous runtime targets.

Recommendation: retain the repository's pinned TypeScript 5.9.3 compiler API first. It already supports the needed primitives and the existing helper uses it. Implement a small traversal policy and reuse current project-resolution code. ts-morph is a viable wrapper, but do not add it and upgrade the compiler in the same change merely to fix nesting. If chosen later, pin compatible versions and prove behavior with the same contract fixtures.

Do not hand-parse TypeScript signatures or imports with regex. Regex is appropriate for filename recognition/filtering only. A class extractInterface helper is not a complete solution for standalone functions, object methods or static/private members.

## 10. Safe phases for the implementation agent

### Phase A — freeze contracts and preserve baseline

Record the confirmed contracts in typescript-helper/README.md before implementation, including the distinct outline and call-list boundaries. Review any remaining unsupported syntax/dispatch limitations without reopening the agreed nested-call scope. Inventory existing CLI actions, Python callers and tests against current main. Record current behavior and the real default invoice fixture. Do not delete Python modules or rewrite Laya/core components.

### Phase B — failing tests for concrete contract changes

Write tests BEFORE production changes and run them to observe meaningful failure:
- Default invoice outline includes exactly two outer functions, excluding reduce/some callbacks.
- Named nested function and local class method are excluded too.
- Production detector rejects .spec.ts/.test.ts/.d.ts; test preset accepts test names and rejects production names; exclusions win.
- Partial service1/invoice-service.ts resolves uniquely; basename alone is ambiguous.
- Generic resolver accepts a test file when explicitly given it.
- Model payload uses readable names mapped to internal source IDs.
- New call-list contract returns canonical paths/signatures for local and imported named calls, without bodies/argument values.
- Calls inside callbacks and nested named functions to implementations outside the selected block are included; target implementations inside the block are omitted.

First tests for an entirely new action may fail because it is absent; follow with real behavioral assertions. An unbuilt helper, missing dependencies or imports failing is not meaningful RED evidence for an existing operation. Never use xfail or relax expectations to conceal the failure.

### Phase C — source utilities in TypeScript

Implement detector/resolver/outline/extraction policies with narrow helpers and the current AST API. Preserve old Python entry points as temporary adapters. Keep the exhaustive parser machinery private where existing extraction/context code depends on it.

Run focused TypeScript tests after each meaningful change. Also keep Python boundary tests for subprocess request/response, timeouts, schema rejection and error mapping.

### Phase D — call navigation and collection compatibility

Add list_called_callables using imports and checker declarations. Cover aliases/re-exports/static methods, full selected-block scanning, internal-target omission and explicit unsupported outcomes. Update the utility contract README with the implemented request/response examples in this same phase. Verify targets can be extracted with their returned path/ID. Reuse resolution helpers with the collectors without replacing their tested depth/size behavior.

### Phase E — core integration and full regression

Switch flow/block callers to corrected public outline and readable choices. Preserve internal selected_id mapping. Adjust old payload-format tests only where the newly approved contract intentionally changes them.

Run TypeScript and Python suites. Core question/rule/enrichment tests remain authoritative. Do not assume previously tested core behavior means integration cannot regress.

Sharon reruns the real Mac default experiment and reads submitted questions, rule decisions and context. The previous method_undecided cause still needs actual rule evidence; do not lower thresholds to force a happy path.

### Phase F — cleanup only after replacement coverage

Remove obsolete implementations only after all callers use replacements, contract tests pass, and compatibility is demonstrated. Keep necessary Python wrappers; moving AST logic does not remove the need for a Python bridge. Update README/setup/API docs, and require a helper rebuild after TypeScript changes.

Use meaningful grouped commits and pushes (for example contracts/tests plus the first completed utility bundle, then call-navigation/integration). Do not push after every test or edit. Record RED evidence before the fix locally, then publish coherent working increments. Tests can be committed locally before code, without a separate remote push.

## 11. Test matrix and existing-test handling

Outline fixtures:
- Plain exported functions and utility scripts.
- Class implementing an interface; static and instance methods.
- Named arrow exports, class callable fields and object methods.
- Nested named functions/callbacks/local class declarations.
- Overloads, get/set accessors, constructor, default export.
- Unicode/CRLF and declaration-only/interface-only files.
- Computed names unsupported or represented as source text; never executed.

Resolution/detection fixtures:
- Production/test/custom regex presets and invalid configuration.
- Quoted/spaced references and line suffixes.
- Exact root/cwd paths; unique and ambiguous partial suffixes.
- Directory-segment collisions, nonexistent paths, inaccessible scans.
- Absolute/outside-root references and symlink confinement.

Call-list fixtures:
- Same-file helper, renamed/default/namespace import, re-export barrel.
- Static class method, repeated same target, recursive/mutual calls.
- External call inside an inline callback is included.
- External call inside a nested named function is included, even if not invoked at runtime.
- A target implemented inside the selected block is omitted, while external calls within its body are included.
- Same-file target outside the block is included; self-reference needs no extra source.
- Shadowed names resolve by symbol identity, not string matching.
- Interface-only or unresolved external implementation; dynamic receiver.
- Path aliases/config support, stale source and missing target.
- Output can be fed directly to extractor; no body/argument leakage.

Keep existing extraction/collector tests. Recursive discovery tests may still be valid for private low-level enumeration, but must no longer define the public file-outline contract. Add replacement public-outline tests first; then explicitly move or revise old tests with rationale. Do not retain two conflicting public contracts or delete coverage wholesale.

Baseline commands, from repository root:
npm --prefix typescript-helper ci
npm --prefix typescript-helper run build
npm --prefix typescript-helper test
python -m pytest -q

No real model dependency for these tests. The user supplies live Mac evidence afterward.

## 12. Errors and production behavior

Log failures using existing log_utils/subprocess diagnostics. Keep missing/ambiguous path, unsupported syntax/target, low model confidence, and true extraction/protocol errors distinguishable.

On an unsafe or unresolved selection, return an explicit no-op/partial result as appropriate and allow normal Claude handling. Do not guess a file or implementation, label all uncertainty inconsistent, or add repeated inference retries. Common supported cases must still work reliably; safe abstention alone is not evidence of good quality.

## 13. Required TypeScript utility contract README

Create or update typescript-helper/README.md as the main contract reference for humans and agents. Sharon must be able to understand and use the utilities by reading this README alone, without opening the implementation files. Link it from the root README and from relevant Python bridge documentation.

Document each public operation: detection, resolution, file outline, callable extraction, called-callable listing, local context collection and project context collection. For each include:
- Purpose and the exact exported method and CLI action name.
- Required/optional inputs, defaults, valid configuration and caller-supplied paths/IDs.
- Copyable request and response JSON, with field meanings and null/empty behavior.
- Exact output scope: what is included, excluded and deduplicated.
- Status/error/partial-result behavior and diagnostic reasons; how the caller should continue safely.
- Supported syntax, known limits and what is not established by static analysis.
- One ordinary example and the important boundary cases, linked to their contract tests.

Include a compact operation index, helper install/build/run commands, Python-to-TypeScript bridge usage, snapshot-bound identity rules, readable names versus internal IDs, source-position conventions and logging location.

Show paired examples proving that file outline excludes nested definitions while call listing still discovers their external calls. Show production/test detector configurations, an ambiguous filename and a successful partial-path resolution, and separate extraction versus dependency navigation examples.

TypeScript exported functions should have brief TSDoc that matches the README, identifying their contract section. Keep detailed behavior in the README instead of requiring readers to reconstruct it from code. Keep the README, method signatures, JSON schema and tests synchronized in each completed phase. Explicitly label planned behavior until implemented; do not describe the new contract as already shipped.

Completion criterion: the next agent can choose an operation, construct valid input, interpret its output and handle a failure using this README alone. Documentation is part of the utility deliverable, not deferred cleanup.

## 14. Deliverable boundary

This document is a proposed contract and phased plan for the next agent. It makes no claim that the new tests have failed or passed, that code has migrated, or that live Laya will choose differently. No repository changes or pushes are part of this planning task.


## 15. Implementation decision appendix (2026-10-30)

The user authorized implementation of phases A–F after the design was frozen. The implemented contracts, evidence and current test status are recorded in `typescript-helper/README.md` and `docs/supporting-utilities-results.md`; sections 1–14 above preserve the original planning snapshot.

Astra resolved the only compatibility ambiguity during implementation: retain `detect_file_references(text, pattern)` unchanged as an explicitly documented temporary Python-regex compatibility API, including compiled flags and conditional syntax. Do not translate arbitrary Python regex into JavaScript. New configured detection and omitted-pattern/default flow execution use TypeScript through a thin bridge. An omitted-argument sentinel distinguishes omission from explicit `None` (invalid) and explicit `DEFAULT_REFERENCE_PATTERN` (legacy).

To preserve core flow gates, its configured lexical guard includes `\\.ts$` with no exclusions, counts complete mentions, then applies its existing production eligibility policy. Filtering test/declaration mentions too early would change `multiple_files`/`excluded`. The flow also checks canonical target eligibility after generic resolution, preserving the existing production-only behavior for symlink aliases. Standalone configured detection still defaults to the production preset.

Readable model choice keys are method identifiers with signatures as descriptions. Unique names use their names exactly; same-name candidates with different signatures use a readable location suffix. Identical-signature candidates retain the existing `ambiguous_candidates` refusal. The CLI keeps the existing `id` field rather than introducing `callable_id`.
