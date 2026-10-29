# Phase 17B — bound expressions, objects and class expressions

Starting revision: Phase17A. Independent test planning and final verification
were completed separately from implementation. A separate design review approved
the new-form signature convention and direct structural scope before coding.
Existing supported signatures are unchanged.

Scope: directly top-level variable-bound arrows/function expressions; members of
object literals/class expressions directly initialized by top-level identifier
variables; direct function/arrow field initializers of supported classes.
Expression async/generator/async-generator forms are included. Raw code/range/ID
and location refer to the callable expression alone. For directly bound
expressions, `name` is immediate external binding/property source spelling,
even when the function expression has an internal name. `signature` is the exact
source slice from the individual binding/property node to callable body start,
trimmed at the end. Thus `selected = (x) =>` labels the binding, while raw code is
`(x) => ...`; signature can begin before code. No declaration-list/statement
prefix or preceding sibling is included; comments/newlines within the binding
header are preserved. Export/const/let keywords outside a VariableDeclaration
are not part of this signature. Method/accessor signatures remain unchanged.

Synthetic matrix: block/concise/typed/async arrows; anonymous/named/generator/
async-generator function expressions; multiple variable declarations; escaped
binding names; object methods/getters/setters, quoted/numeric property names,
function/arrow properties, async-generator object methods; named/anonymous class
expressions, constructor/static methods, readonly/private fields, declared-class
function fields. LF/CRLF and astral prefixes pin exact source, UTF16 location,
IDs, distinct same-named ranges and no writes. A multiline commented binding
header pins the distinction between signature and exact extracted expression.

Nested callbacks/functions/objects/classes, computed names, destructuring
bindings, parenthesized/as/satisfies/non-null wrappers and anonymous default
exports remain unsupported diagnostic forms for17C. Noncallable property values
and shorthand aliases introduce no new callable implementation. Parser errors
still fail; no source execution or dependency completeness is claimed.

TDD: new expression matrices failed with empty callable lists, binding-header
case had no candidate, both full hook cases failed at missing candidates before
implementation. Updated old unsupported expectations intentionally promote field
arrows/class expressions/top-level bound arrows, preserving computed/nested and
special-declaration diagnostics; Python's old unsupported-form case now has a
computed member diagnostic while positively checking the promoted arrow too.
The two new real-hook subprocess cases assert binding label at actual SDK request,
exact expression-only raw code and provenance, unchanged source and partial
coverage. Only laya_mlx is mocked (mock-hook/.2/fr), not helper/flow/interpreter.
All previous whole-rendered-context/Unicode/stdout/no-op tests remain required.

Implementation: typescript-helper/src/index.ts; no Python runtime changes.
Environment unchanged Python3.12.14/pytest9.2.0, Node24.22.1/TypeScript5.9.3.
Baseline fresh build, Node10/10, Python354/354 passed86.92s. Focused corrected
build/Node14/14 and3 Python cases pass. Final exact-byte implementer gate:
fresh TS build/typecheck and Node14/14 passed; Python356/356 passed80.68s.
The independent verifier inspected the actual diff/new matrix/record and independently
reran fresh build/typecheck, Node14/14 and Python356/356 in92.22s. All final runs
had zero skips/xfail/failures; git diff --check clean. A trailing space caught in
preverification diff inspection was removed; the complete writer gate was
repeated afterward. No behavioral review blocker remained. Evidence2026-10-29.
Live Laya/SDK/Claude versions unavailable; no actual calls or activation.
Real compatibility remains blocked/unrun until20. Fixture provenance: synthetic.
Verifier verdict: VERIFIED for stated17B scope. Decision: COMPLETE.
