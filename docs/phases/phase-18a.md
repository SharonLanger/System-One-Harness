# Phase 18A — bounded same-file semantic collection

Starting revision: Phase17C. Independent test planning and a separate design
review preceded implementation. This increment adds a direct helper/bridge API;
flow and hook integration remains the next increment. Independent verification
is complete.

`collect_local_context(path, callable_id, max_depth=2,
max_dependency_chars=12000)` returns the existing exact selected extraction plus
`coverage: partial`, dependencies, gaps and collection accounting. The CLI action
is `collect_local_context`; its limits use the same snake-case names. The direct
TypeScript function is `collectLocalContext` with `maxDepth` and
`maxDependencyChars` options. Existing outline/extract APIs remain unchanged.

One source read supplies the parser, isolated TypeScript semantic checker,
source hash, selected raw code and dependency slices. The compiler host supplies
only that snapshot: no import, library or configuration files are loaded, and no
project code is executed. References use compiler symbol identity, including
import/local aliases and shadowing. Dependency `symbol_ids` serialize sorted
same-file declaration hash:start:end identities; emitted unit IDs separately
identify raw source ranges. Several symbols may map to one complete statement.

Module variables emit whole original statements, imports whole import statements,
and types/functions/classes whole declarations. Same-class referenced fields and
methods are eligible; the selected class constructor is included separately.
Outer-function locals/parameters and external nested callees are closure gaps.
Class text and constructors do not establish runtime initialization or dispatch.
Mutable declarations, imported implementations, computed references and unresolved
symbols remain explicit gaps. Bare side-effect imports, top-level expression
statements and reexports receive module-effect gaps. Other module initialization
effects are unanalysed and are not fully enumerated. A bound callable's immediate
binding header/type is inspected even when it precedes the raw callable range.
Parent/child and atomic statement overlaps are valid and remain unmodified.

Admission uses breadth-first traversal, selected references at depth1; final units
sort by start/end. Equal units are deduplicated and symbol provenance is merged.
Depth0 is supported; maximum20. Dependency budget is positive and at most1,000,000
UTF16 code units, counting each complete dependency `code` including overlap.
Selected code and metadata are excluded. Omitted units produce depth/size gaps
and are not expanded. This budget is separate from model-input and final hook
rendering budgets. The Python bridge checks selected provenance, dependency
path/hash/ID, UTF16 lengths, sorted unique unit/symbol IDs, gap ranges and accounting.

Synthetic tests cover imports, local aliases, constants/types, shadowed parameters,
cycles, class fields/constructors, closures, mutable state, dynamic/unresolved calls,
side-effect imports, atomic sibling/class units, overlapping selected statements,
LF/CRLF, astral UTF16 positions, exact whole-unit/depth budgets, deterministic
results, stale IDs and malformed bridge provenance. Expected source statements
are manually specified independently of the collector. Existing tests are retained.

Tests-first evidence: all6 initial collector tests failed because the function
was absent; Python collection failed because the bridge API was absent. One later
overlap test initially used a self-reference already represented by the selected
binding; it was corrected to reference a sibling declaration in the same atomic
statement, which establishes the intended overlapping-unit case.

Environment: Python3.12.14/pytest9.2.0, Node24.22.1, TypeScript5.9.3.
Baseline: fresh build/typecheck, Node19/19, Python358/358 passed78.03s.
Focused checks: Node7/7 and Python16/16 passed. Final implementer gate:
fresh build/typecheck, Node26/26 and Python374/374 passed89.49s, with zero
failures/skips/xfail; git diff --check clean. Independent final verification reviewed the complete diff and outgoing public
documents, then reran fresh build/typecheck, Node26/26 and Python374/374 in92.78s.
All final runs had zero failures/skips/xfail; git diff --check clean. The review
requested precise module-effects and progress-scope wording, now resolved; no blocker remains.
Evidence date:2026-10-29. All fixtures synthetic; Laya remains mocked through
accumulated pipeline tests. No actual model/SDK/Claude activation. Real Laya
compatibility remains deferred until20; explanation quality and universal
context sufficiency are not established.
Verifier verdict: VERIFIED for Phase18A helper/bridge scope.
Decision: COMPLETE for18A; flow/hook integration remains pending.
