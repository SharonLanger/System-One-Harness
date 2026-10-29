# Phase 17A — named class declaration callables

Starting local commit: `a1ffad6`, exact tree of published `c6720f3`.
Environment unchanged: Python3.12.14/pytest9.2.0, Node24.22.1,
TypeScript5.9.3. Independent preimplementation planner and final verifier:
`/root/phase17_builder/phase17_reviews`, Luna Medium (separate from writer).

Scope: ordinary top-level functions plus members with bodies in named top-level
class declarations. The advertised synthetic matrix covers constructor parameter
properties, instance/static/public/private/protected/#private methods, getters,
setters, async/generator/async-generator methods, decorated methods, overload
implementation bodies and duplicate names across classes. Names retain member
source spelling (`constructor` for constructors, property name for either
accessor); signatures retain modifiers/get/set and decorators. Opaque IDs use
hash:start:end, so same-spelled members in different scopes remain distinct.
No schema field or selection representation changes. Signatures contain member
headers, not reconstructed enclosing classes. No type-check or model-accuracy
claim follows from parse-only fixtures.

Tests were written first: Node matrix LF/CRLF tests failed with empty callables,
and both full-hook cases failed before implementation at their missing candidate.
The previous class-unsupported expectations in outline.test.cjs and
test_callable_source.py deliberately promote the class member while keeping
arrow/nested/top-level async/generator/function-overload expectations unchanged.
Each matrix unit has an independently specified exact raw/signature oracle,
UTF16 offsets/locations, hash/ID, display text, comments, no writes and stale-ID
checks. Abstract/ambient/overload signature-only members remain diagnostic,
not selectable. Class-expression, nested-class, computed-member and field-arrow
forms remain diagnostic until later increments. Parser errors remain fatal.

The new hook scenario runs the actual adapter, flow, bridge/compiler, selection,
enrichment, policies and extraction, with only child laya_mlx replaced. It selects
an async class method, checks independently stated exact raw code/signature and
location, partial coverage, provenance and pure protocol stdout. The complete
rendered context fits at its exact Unicode character ceiling and refuses one
character below; no truncation. Source bytes remain unchanged. Simulated model
mock-hook/temperature .2/lang fr; actual SDK/model/harness unrun, deferred Phase20.

Implementation: typescript-helper/src/index.ts; no Python runtime change.
Fixture provenance: purpose-built synthetic TypeScript, not private project code.
Dependencies, closures and enclosing fields are not collected; context is partial.
17B will cover bound expressions/objects/class expressions; 17C will complete
recursive/special callable coverage and the advertised Phase17 matrix.

Baseline fresh build passed, Node6/6 and Python352/352 passed (86.02s).
Astra High `/root/phase17_builder/source_repairs` diagnosed a self-review naming
regression before correction: generic getText would expose escaped ordinary
function identifiers differently. A red regression proved this; the correction
keeps the previous semantic function name while retaining documented textual
member names. Original signature/code spelling remains exact. Luna independently
identified the same issue during diff inspection.
Final implementer gate: fresh build/typecheck passed; Node10/10 passed;
Python354/354 passed in72.10s. Independent Luna reviewed the complete diff,
including new matrix/record, and independently reran fresh build/typecheck,
Node10/10 and Python354/354 in80.45s; diff check clean. Both final runs had
zero failures/skips/xfail. Evidence timestamp:2026-10-29. No required check unrun
within17A; live model/SDK and actual harness checks remain explicitly deferred.
Independent finding resolved: escaped ordinary function name compatibility
(above); no remaining blockers. Verdict: VERIFIED for stated17A scope.
Decision: COMPLETE. Remaining17B/C and18–19 are authorized, not yet implemented.
