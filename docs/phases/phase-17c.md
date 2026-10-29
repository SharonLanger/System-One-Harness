# Phase 17C — recursive and special runtime callable forms

Starting revision: Phase17B. Independent test planning and a separate design
review preceded implementation; independent final verification is complete. The advertised
Phase17 matrix is divided across the17A,17B and17C records.

Runtime implementation bodies are now discovered recursively: local functions,
callbacks, local binding expressions, nested objects/classes and class fields;
async/generator/async-generator function declarations; overload implementations;
anonymous default function and default-class members; computed members and
transparent-wrapped binding expressions. Source order is deterministic, with
parent before child when ranges overlap. Each retains its own hash:start:end ID,
UTF16 location and exact raw source. A parent includes nested code in its raw slice;
selecting a child extracts only that child, never the enclosing body.

Named function declarations retain semantic identifier names. Immediate simple
variable/property bindings take naming precedence over internal function-expression
names. Other member/function-expression names retain source spelling; computed
keys include their brackets and are never evaluated. Anonymous default function
declarations use `<default>`; other unbound anonymous callables use
`<anonymous@line:column>` with 1-based UTF16 coordinates. A callback beneath an
export is not itself named default. No enclosing lexical environment is collected.

Binding inference crosses only parenthesized, as, satisfies, non-null and type
assertion expression edges, requiring each wrapper to own that exact expression
and the binding initializer to own the outermost wrapper. It never crosses call,
new, await, conditional, binary/comma or arbitrary ancestor nodes. Binding-aware
signatures remain exact source headers through body start, including opening
wrappers; they need not be balanced standalone programs. Raw code/ranges still
refer only to the underlying callable expression. Existing17A/B signatures remain
unchanged. Direct or wrapped destructuring-bound callables remain explicitly
unsupported; independently nested callbacks within them are still discovered.

Bodyless runtime declarations (abstract/ambient members, declare functions and
overload signatures) remain individual unsupported_callable diagnostics, while
an overload implementation body is selectable. Type-only function/constructor/
interface call signatures are intentionally outside runtime implementation
extraction and do not produce spurious diagnostics on ordinary annotations.
An explicit limitation states this boundary. Parser errors still fail rather
than returning recovery outlines. Parsing never imports or executes source.

Tests-first evidence: the new recursive matrix exposed only2 of24 expected
callables before implementation, wrapper matrix0 of8, and both hook cases lacked
their expected candidate. Existing deliberately unsupported expectations now
positively assert promoted runtime forms while retaining bodyless/destructuring
diagnostics. The prior Python unsupported-form case now uses an abstract member
instead of the promoted computed method. No regression case is removed.

Synthetic fixtures cover overlapping parent/child slices and duplicate names;
escaped overloaded identifiers; default function/class forms; computed identifier,
property-access/string/numeric/template/callback keys; each wrapper and stacks;
negative binding inference; declaration-only/type-only distinctions; LF/CRLF,
astral characters, exact signatures/raw/display/IDs/locations, stale IDs and
unchanged files. A side-effect-looking computed key must not create a marker.
Two complete hook subprocess cases select a nested bound arrow and anonymous
default function, check exact source/provenance, partial coverage and actual
question labels. Only laya_mlx is replaced with fixed mock-hook/.2/fr responses.
All previous final-context budget, native stdout and no-op checks still apply.

Implementation: typescript-helper/src/index.ts. No Python runtime changes.
Environment: Python3.12.14/pytest9.2.0, Node24.22.1, TypeScript5.9.3.
Baseline: fresh build/typecheck, Node14/14 and Python356/356 passed76.24s.
Focused new-form gate: fresh build/Node19/19 and3 Python cases passed before
additional matrix parameters. Final implementer gate: fresh TypeScript
build/typecheck, Node19/19 and Python358/358 passed82.18s. Independent verification
inspected the final implementation, all test changes and complete outgoing public
documents, then reran fresh build/typecheck, Node19/19 and Python358/358 in74.94s.
All final runs had zero failures/skips/xfail; git diff --check clean.
Evidence date:2026-10-29. No independent review blocker remained.
All fixtures are synthetic. No actual model/SDK/Claude execution or activation.
Live compatibility remains blocked until20; dependency context remains partial
until18/19, and general model-selection accuracy has not been evaluated.
Verifier verdict: VERIFIED for the advertised Phase17A/B/C callable matrix.
Decision: COMPLETE for Phase17.
