# Name-based TypeScript utilities for Python — implementation plan

Status: PLAN ONLY. Do not implement until Sharon explicitly starts the implementation.
Repository: SharonLanger/laya-context-router
Reviewed main: b140f48977766e6bae62107f263b38e79d5d895f
Date: 2026-10-31

## Goal and boundaries

Give Python callers four small utilities:
1. Given a file, list its methods/functions and signatures.
2. Given a file and method name, return that implementation's exact code.
3. Given a file and method name, list the methods it calls.
4. Given a file and method name, list methods that call it.

Source analysis remains in TypeScript. Python provides transport, validation and a simple public interface. IDs/hashes remain internal. Every returned file path is relative to an explicit analyzed project root, not process cwd, hook cwd or this tool's installation directory.

Add new APIs. Preserve existing ID-based exports, CLI actions, Python functions, schemas and behavior. Do not change flows/hooks or automatically feed these results to LAYA or Claude. No model calls are needed.

"Method" includes supported functions, class methods, bound arrow/function expressions and object methods already handled by the helper. This plan does not expand syntax support.

## Instructions for Sol

Implement in a separate implementation PR based on current main. If this plan is still unmerged, copy its document into the implementation branch or base work on the plan branch without merging anything automatically. Reference the plan PR in the implementation PR.

Before editing, read applicable AGENTS.md files, this plan, existing utility code and tests; compare current main with the reviewed baseline. Do not overwrite concurrent work.

If anything materially diverges from this plan—unexpected failure, incompatible existing behavior, ambiguous contract, required scope expansion or a proposed shortcut—pause the affected work and consult the planning/reviewer agent (Astra). When agent tools are available, ask/spawn Astra with the expected behavior, evidence, failure output and smallest proposed resolution. If Astra is unavailable, ask Sharon instead. Never silently change the contract, weaken tests, broaden scope or implement deferred features. Routine choices that preserve the contract do not need escalation.

Report decisions and verification in the PR. Stop after preparing the implementation PR; do not merge or deploy without separate authorization.

## Current implementation and evidence

Existing TypeScript code:
- typescript-helper/src/index.ts: public outline and exact extraction; local context.
- typescript-helper/src/calls.ts: old listCalledCallables and getCalledMethodLocations.
- typescript-helper/src/incoming.ts: getCallingMethodLocations.
- typescript-helper/src/cli.ts: JSON actions.
- src/laya_context_router/building_blocks/typescript.py: existing Python transport and strict validators.

The public outline, extraction and outgoing navigation already contain signatures. Incoming caller records lack signatures. Extraction already exists by internal ID. New name-based wrappers should reuse these capabilities, not rebuild semantic analysis.

Review evidence from this conversation: a disposable copy of the helper built with pinned TypeScript 5.9.3; the two existing navigation suites passed 46 tests, with no skipped cases. Additional disposable probes confirmed callback scanning, injected receiver uncertainty, reassignment gaps and unrelated project warnings. This was focused verification, not a full-repository run or proof of a real-world coverage percentage.

Current incoming lookup can retain callers alongside dynamic_dispatch diagnostics. It can also report project-wide uncertainty from unrelated computed invocations. Current outgoing lookup may return status ok for a reassigned receiver's declared implementation. These facts constrain the policy below.

## Proposed Python public API

Add an additive module:
src/laya_context_router/building_blocks/typescript_methods.py

Proposed entry points:

~~~python
list_methods(file, *, project_root, ...)
get_method_implementation(file, method_name, *, project_root, ...)
list_called_methods(file, method_name, *, project_root, ...)
list_calling_methods(file, method_name, *, project_root, tsconfig_path, ...)
~~~

The optional transport settings should follow existing node/helper/timeout conventions. Caller lookup requires an explicit tsconfig path to define the searched project.

Public file/config inputs are project-root-relative strings. project_root must be an absolute existing directory. Reject absolute file/config arguments and root escapes clearly. Accept normal nested paths, spaces and Unicode using the existing confinement rules. Outputs use canonical root-relative paths with forward slashes. Do not guess a root.

Use exact, case-sensitive method-name strings. Do not accept IDs, parse signatures to select methods, use fuzzy matching, select by source order or introduce a qualified-name syntax in this first version.

Names are resolved against the existing public outline:
- One match: use its current ID internally.
- No match: error with method_not_found.
- More than one match: ambiguous with data null. Return no candidates, code or guessed selection.
- Duplicate names in different classes in the same file remain ambiguous, even if their signatures differ.
- Overload signatures continue to follow the existing outline: the body-bearing implementation is one callable.

list_methods may list duplicate names as separate records with signatures and lines, because it makes no selection. Subsequent name-based lookup must still reject ambiguity. Signatures are informational, not an alternate public identity.

## Public result contract

All four utilities return one envelope:

~~~json
{
  "status": "ok",
  "data": {},
  "diagnostics": []
}
~~~

Allowed statuses:
- ok: usable data for this utility's documented static scope.
- uncertain: skip this operation's entire result; data is null; at least one concise diagnostic.
- ambiguous: multiple selected-name matches; data is null; diagnostic ambiguous_method.
- error: input/source/config/transport/validation failure; data is null; concise diagnostic.

Public diagnostics contain a stable code and short safe message, optionally a root-relative path/location when meaningful. Do not copy raw exceptions, tracebacks, absolute paths or IDs into the public response. Detailed original failures may use existing logging. Preserve existing raw APIs' behavior.

A successful empty method/call list is valid and distinct from an error. An empty incoming list means no explicit callers found in the reported static scope; it never means unused everywhere.

Method metadata:

~~~json
{
  "file": "src/work.ts",
  "name": "work",
  "signature": "export function work(value: number): number",
  "start_line": 3,
  "end_line": 5
}
~~~

Signatures preserve declared source headers/types. Do not infer omitted return/parameter types, invent annotations, or expose nested bodies through signature metadata. Return no id, callable_id, source_hash or other opaque identity fields in these new public results. Do not redact words such as "id" or hash-looking strings inside actual source code.

Data shapes:
- list_methods: {methods: [method metadata]}
- get_method_implementation: {method: method metadata, code: exact existing extractor code}
- list_called_methods: {methods: [method metadata plus call_sites]}
- list_calling_methods: {callers: [method metadata plus call_sites], scope: existing scope projected to root-relative paths without opaque identities}

call_sites contains file, start_line, start_column, end_line, end_column. Definition lines are one-based and inclusive; call sites use one-based UTF-16 columns and exclusive ends. Preserve all distinct invocation sites and deterministic ordering. Navigation returns no bodies; callers can loop over results and request implementations separately.

The implementation's code is exactly the existing extraction output, including its established exclusion of leading comments. Do not add supporting dependencies or a full-file fallback.

## Identity and round-trip rules

Every returned navigation method must be usable as file + name with get_method_implementation:
- Resolve the target/caller's supported public-outline identity internally.
- For outgoing class-qualified display names, derive the matching public outline name from its ID; do not split display strings heuristically.
- If the name is duplicated, the target is not a selectable public-outline callable, or the incoming record is module-level/anonymous without an addressable method, return uncertain with data null for this navigation operation.
- Do not silently substitute another same-named callable or invent a method for a top-level statement.
- Keep all internal path/ID values unchanged while delegating to old utilities.

This conservative boundary can reject a navigation result even when the old ID-based API can address it. That is acceptable: the new public interface prioritizes unambiguous file/name identity.

## Uncertainty and error policy

For the two new navigation entry points:
- Underlying ok: validate/project metadata, enrich signatures and enforce round-trip identity.
- Underlying partial: return uncertain with data null. Do not forward its caller/target list.
- Underlying error: return error with data null.
- If signature enrichment or identity projection fails for any item, return uncertain or error as appropriate for the whole operation; no half-built list.

This deliberately treats project-wide warnings conservatively too. It may discard valid hints because an unrelated file contains a dynamic call, or because a library/callback-related warning accompanies a valid target. Do not build per-result confidence classification or diagnostic attribution now.

list_methods and get_method_implementation use existing outline/extraction validation. Existing informational scope limitations alone are not failures; unsupported sibling syntax should not automatically invalidate a valid selected implementation. If no trustworthy requested result exists, return an explicit error/uncertain outcome, never invented data.

Normalize expected missing-file/root, invalid-name/config, Node/helper startup, subprocess timeout/nonzero exit, malformed JSON/schema and helper failures at the new public boundary. These must not escape as ordinary unhandled exceptions. Do not swallow cancellation/interrupt signals or change error behavior in the old Python adapter.

These utilities do not send errors to a model. Future consumers should:
1. Use the selected implementation when extraction succeeds.
2. Add navigation hints only when that navigation operation is ok.
3. Skip uncertain/ambiguous/error navigation while retaining the independently successful implementation.
4. Describe results as static related declarations, not a guaranteed runtime call graph.

## Implementation approach and permitted changes

Prefer a small TypeScript facade, such as typescript-helper/src/named.ts, for root validation, name-to-ID resolution, delegation and public metadata projection. Add four distinct CLI actions and exports; preserve every old action.

Incoming signature enrichment should reuse exact extraction/current callable metadata privately. Avoid changing the old incoming schema: its Python validator enforces exact fields. Repeated internal extraction is acceptable; caching, persistent services and batch protocols are not required.

Keep Python thin; it must not interpret TypeScript source, resolve symbols, split ID encodings or duplicate AST traversal. Reuse existing subprocess transport/logging through a minimal shared internal helper if necessary, preserving existing consumers.

Expected edited/new paths:
- typescript-helper/src/named.ts (or equivalent additive facade)
- typescript-helper/src/index.ts and cli.ts (additive exports/actions)
- src/laya_context_router/building_blocks/typescript_methods.py
- focused TypeScript/Python tests and fixtures
- typescript-helper/README.md and this plan's completion/evidence notes

Do not change flow decisions, hooks, LAYA questions/rules, experiment behavior, dependency versions, build-output architecture or existing public schemas. Build products remain under root build/ and untracked. If a nontrivial core modification becomes necessary, consult Astra before expanding scope.

## Accepted gaps — record, do not fix

1. Reassigned receiver/object method: old outgoing analysis can return the declared/original implementation with ok despite later reassignment. The new facade cannot claim to eliminate this. Document it as an accepted static-analysis limitation.
2. Function/method passed directly as a callback: incoming analysis may omit its indirect invocation, including an ok empty list. Accepted incompleteness; do not add data-flow analysis.
3. Dynamic indexing, injected/interface receivers, unsupported inheritance, call/apply/bind, constructors and advanced anonymous cases: keep existing support limits; translate reported partial outcomes to uncertain.
4. Calls inside an anonymous callback to an external named helper remain important. Preserve existing discovery. The callback itself does not need to become a public method.
5. Module-level or non-addressable callers can remain unsupported by the new name-based interface, with an explicit uncertain outcome; preserve old API results.
6. JS/TSX, multiple projects, package implementations and unsupported syntax remain outside current support.
7. No new source-change-during-analysis work, resource-budget redesign, caching or performance project. Preserve existing safeguards and transport timeout handling.
8. Incoming project-wide warnings may suppress otherwise useful navigation hints under this first conservative facade.

Do not promise 80–90% coverage or prove runtime dispatch. These are context aids; Claude can investigate omitted dependencies using the supplied code.

## Focused acceptance tests

Use real TypeScript fixtures and pinned compiler. Mock only transport failures where appropriate.

A. Public naming and extraction
- Listing exposes names, signatures and definition lines, with no opaque metadata.
- Unique file/name extracts exact code and preserves source line endings/Unicode.
- Missing name/file, malformed source, invalid root and invalid argument types return explicit outcomes.
- Same name in two classes yields ambiguous, null data and no candidate leakage.
- Different signatures do not silently disambiguate duplicate names.
- Overload implementation follows existing outline identity.
- Declared signature types survive; inferred types are not fabricated.

B. Navigation
- Same-file and imported direct calls round-trip through file/name extraction.
- Static methods and straightforward instance methods retain signature and correct locations.
- Alias/re-export resolution stays semantic; unrelated same-name functions are excluded.
- Repeated calls produce one method entry with all distinct sites.
- Calls inside callbacks are still discovered by the old engine. When it returns partial, the facade returns uncertain, not a fabricated ok hint.
- Incoming signatures are present for ordinary named callers.
- Incoming injected-parameter example returns uncertain and null data, even though old API returns a caller plus dynamic_dispatch warning.
- An unrelated computed call causing an old project-wide warning also maps to uncertain; lock this deliberate conservative policy.
- Non-addressable/module callers and duplicate-named returned targets yield uncertain, not misleading public identities.
- Empty successful results retain their narrow documented meaning.

C. Boundaries and compatibility
- Run from project root, nested cwd and unrelated cwd: same root-relative inputs produce identical public paths.
- Existing root confinement continues; no prefix-collision/root-escape acceptance.
- No new public result contains opaque identity metadata; actual code/signature literals remain unchanged.
- Missing Node/build, timeout, malformed JSON/schema, and nonzero helper exits produce public error responses with no raw stack trace.
- Old exported functions/actions and strict Python validators retain exact contracts.
- No new utility is invoked by a flow/hook; no model call occurs.
- Characterize accepted reassignment/direct-callback gaps without turning them into new feature requirements.

## Execution and PR checklist

1. Inspect latest code and instructions, establish baseline checks, and confirm the four public contracts.
2. Add focused behavior tests; observe meaningful failures for missing APIs/behavior.
3. Implement the additive TypeScript facade and CLI actions.
4. Implement thin Python wrappers, validators and safe expected-error normalization.
5. Update README with four Python examples, project-root paths, statuses, duplicates, static-scope caveats and accepted gaps.
6. Run:
   - npm --prefix typescript-helper ci
   - npm --prefix typescript-helper run build
   - npm --prefix typescript-helper test
   - python -m pytest -q
   - git diff --check
   Use the current repository's environment/setup instructions; do not change dependencies to get a green run.
7. Review diff for API compatibility, no IDs in new metadata, no flow/hook changes, and no accidental deferred-feature work.
8. Open/update the implementation PR with concise problem/behavior summary, exact tests run and failures/skips, accepted gaps and any Astra decisions. Do not claim live Mac/model verification.
9. Tell Sharon the implementation PR is ready for review. Do not merge automatically.

The documentation-only planning PR must contain this plan only. It does not authorize executing the steps above until Sharon asks.
