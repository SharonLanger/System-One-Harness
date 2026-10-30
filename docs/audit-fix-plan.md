# Audit follow-up: test commits and implementation plan

Decision date: 2026-10-30. This plan incorporates Sharon's review and supersedes
the original audit's remediation recommendations where they differ below.
Scope: prepare tests first, then fix accepted behavior in separate commits.
This document records the original plan. Implementation and commit completion
are recorded in audit-fix-results.md.

## Accepted decisions

| Finding | Decision | Required behavior |
| --- | --- | --- |
| F01 shorthand dependencies | Fix | Preserve dependencies referenced through object shorthand, including imports. |
| F02 indistinguishable methods | Fix with no-op | Detect identical candidate descriptions before inference; provide no extra context and let Claude handle the original request. Owner-enriched selection is not the V1 solution. |
| F03 filename detection | Fix | Improve the default regex; return all matching .ts paths, then separately decide flow eligibility. |
| F04 singleton choice gap | No action | Sharon considers this a non-issue for this scope. Do not import the audit failure into the active suite. This case concerns choice, not noul. |
| F05 huge numeric values | Skip for V1 | Do not add an active release-blocking test or change numeric validation in this work. |
| F06 declaration-only dependencies | Fix | Include the declaration as useful context and explicitly flag that its implementation is unavailable. Apply consistently to local/project collection. |
| F07 Unicode line separators | Backlog | Discussed; no implementation requested. Do not bundle into these fixes. |
| F08 duplicate configuration keys | Documentation; skipped tests | Explain unique-key configuration authoring. Preserve existing validation; defer extra rejection in legacy loaders. |
| F09 concurrent symlink replacement | Skipped scenario | Retain as a deferred filesystem scenario, not a V1 acceptance blocker. Ordinary source edits are different. |

Live model accuracy, Claude integration, and token-savings measurement remain a
separate validation milestone. No new live execution was authorized by this plan.

## Repository preparation before committing

The working directory used for the audit is a reconstructed snapshot of
SharonLanger/laya-context-router at
00db206cae46fa508bba3fe62c11c57c95df4668. Its local Git index was created for an
existing tracked-fixture test; it is not a normal clone with repository history.
Do not commit its entire staged tree or use git add --all.

Obtain a normal checkout of the current remote branch, create an audit-follow-up
branch, and compare relevant implementation/tests with the audited revision.
Port only the listed new tests/docs and the small README documentation link.
If upstream already fixed a finding, retain the useful regression test and
record that the implementation commit is unnecessary. Read any current AGENTS.md.

## Commit 1: agreed regression tests and V1 scope

Suggested title: `test: capture reviewed context-routing regressions`

Include these six new files:

- tests/test_context_shorthand.py — six constant/function/import cases across
  local and project collectors.
- tests/test_method_ambiguity_fallback.py — two no-op cases, for class and object
  methods. Assert no model prediction, no context, and noop status.
- tests/test_prompt_file_list.py — thirteen extraction lists, three routing
  regressions, and one real-multiple-files no-op control.
- tests/test_declaration_context_contract.py — two cases requiring both the
  declaration text and the declaration_only gap.
- tests/test_file_method_context_deferred.py — one explicitly skipped filesystem
  replacement scenario with a V1 scope comment.
- tests/test_configuration_duplicates_deferred.py — two explicitly skipped
  legacy-loader rejection scenarios.

Include docs/configuration-conventions.md, this plan, and the README link to
configuration conventions. The original external audit bundle is historical
evidence, not the acceptance suite: do not import all its failures wholesale.
In particular, its F02 uniqueness assertions are superseded by no-op behavior.

This tests-first commit is intentionally red on the audited implementation.
Keep it on the work branch until the fix commits make the accepted suite green.
Do not hide accepted defects with skip or xfail. Only the explicitly deferred
scenarios above are skipped. Do not merge the red checkpoint independently.

## Commit 2: shorthand dependency resolution (F01)

Suggested title: `fix: retain dependencies referenced by object shorthand`

Inspect identifier handling in typescript-helper/src/index.ts and project.ts.
For a shorthand property, resolve its referenced value symbol rather than stopping
at the property's own symbol. Reuse existing alias/import traversal, source-unit
deduplication, confinement, depth, and character budgets. Do not include every
same-named declaration or recursively traverse unrelated code.

Expected example: const value=42; function chosen(){return {value};} includes the
value declaration, exactly as the explicit {value: value} form does. In project
mode, an imported value includes its import and the resolved implementation.

Validation: six new regressions plus existing local/project dependency tests.
Add focused controls for shadowed names, repeated shorthand references, and
explicit properties so a broader symbol lookup cannot collect the wrong binding.
Rebuild the helper before Python bridge tests; otherwise they can use stale JS.

## Commit 3: ambiguous candidate no-op (F02)

Suggested title: `fix: skip enrichment for indistinguishable method candidates`

Detect duplicate candidate descriptions before model prediction, preferably at
the shared method-selection boundary so direct block calls and the flow agree.
Use the existing selection-result contract and a clear diagnostic reason such as
ambiguous_candidates. The flow must return noop with context=None. Preserve the
original prompt and normal Claude continuation.

V1 is conservative: if the candidate set contains indistinguishable descriptions,
skip enrichment even if the prompt names an owner. Do not introduce a model retry
or attempt to select by arbitrary IDs. Distinct candidate signatures must still
work, including different signatures with the same method name.

Validation: the two added cases; direct block coverage; a successful distinguishable
candidate control; and hook-level confirmation that no extra context is emitted.
Spy on loading as well as prediction where possible to prove early detection.

## Commit 4: extract the complete .ts filename list (F03)

Suggested title: `fix: restrict default prompt file detection to ts paths`

Keep the reusable detector's caller-supplied-pattern API and FileReference metadata.
It already returns a list; the new tests compare the .path projection. Do not
replace its records with strings and break downstream callers. The default flow
pattern should match the V1 suffix list [".ts"] with exact suffix boundaries.

Contract:

- Return every match in prompt order, preserving directories and duplicate mentions.
- Ignore Parser.parse, Object.keys, decimals, unsupported suffixes, and partial
  matches inside a.tsx or a.ts.bak.
- Preserve supported quoted paths with spaces and :line:column locations; those
  locations and quotes are not part of the returned path.
- Detect .spec.ts, .test.ts, and .d.ts as filenames; flow eligibility excludes them.
- Detection performs no filesystem reads and does not pick one file from a list.
- More than one mention still causes the current flow to no-op. Duplicate mentions
  remain preserved; changing their eligibility is outside this decision.

Examples: `Compare main.ts and src/parser.ts` returns
["main.ts", "src/parser.ts"]. `Explain main.ts: why 1.5?` returns ["main.ts"].

Validation: all seventeen new cases; existing custom-regex and path/span tests;
existing excluded-file and multiple-file controls. Some existing expectations for
an unsupported extension may need deliberate alignment, but no context may be
injected for an unsupported target. Avoid accidental substring matches.

## Commit 5: declaration text with explicit gap (F06)

Suggested title: `fix: include declaration context with implementation gaps`

Local collection already retains declare function text but lacks its specific gap.
Add declaration_only when a referenced target has no body. Project collection
already emits that gap but must also retain the useful declaration source unit.
Reuse existing dependency representation, budgets, ordering, and deduplication.
Do not present a signature as an implementation or execute declared code.

Validate both added cases, an implemented-function control without the false gap,
and existing overload behavior: an overload signature with a resolvable body is
not an implementation-missing case. Preserve repository confinement and existing
policy for external/declaration files; do not expand reads beyond approved scope
merely to provide a signature. Confirm hook rendering includes the declaration
and makes the gap visible to Claude.

## Final verification and delivery

After targeted checks pass, build the TypeScript helper, run its complete Node
suite, and run the complete Python suite. Record actual totals and skip reasons.
The audit baseline was 427 Python and 53 Node passes; these are historical counts,
not guarantees for a newer checkout. The reviewed additions comprise 31 cases, including the direct ambiguity-block control.
Run git diff --check and inspect the staged paths before each commit.

Deliver the ordered test/fix commits together with a concise description of
behavior changes and test evidence. Preserve skipped scenarios and the remaining
live-validation limitation. Do not claim real-model accuracy or token savings
from mock-backed passing tests.
