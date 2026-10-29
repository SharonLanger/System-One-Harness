# Phase 19A — confined project-aware dependency collection

Starting revision: Phase18B. Independent test planning and a separate design
review preceded implementation. Independent final verification is complete.
This increment adds a separate helper/bridge API; flow/hook integration remains
Phase19B. Existing local collection and extraction remain available unchanged.

`collect_project_context(path, callable_id, repository_root=..., max_depth=2,
max_dependency_chars=12000)` returns exact selected source plus partial project
context. CLI action is `collect_project_context` with `repository_root` and the
same snake-case limits. TypeScript API `collectProjectContext` takes
`repositoryRoot`, `maxDepth` and `maxDependencyChars` options.

The nearest confined tsconfig is parsed by TypeScript, including relative
extends, include membership, baseUrl and paths. Actual Classic/Node10 module
resolution is supported. Modern condition-dependent modes, including implicit
NodeNext defaults, explicitly fall back to local context with an unsupported-mode
gap; they are never approximated as Classic. Missing/malformed configuration or
project-membership mismatch likewise returns intact local context with a gap.
Configuration inspection precedes selection of the local/project snapshot path.
`project` records repository root, leaf config path/hash and sorted hashes of
consumed configuration/module JSON metadata; the leaf hash alone is not an
effective-configuration identity.

A root-only compiler program follows the resolved graph without automatic
libraries/types, project plugins or module execution. Each source is read once
and cached by canonical path and SourceFile object identity. Per-file snapshots
are coherent; no atomic snapshot of the whole live repository is claimed.
Raw source units retain each file's hash, UTF16 ranges and text. Unit identity
is `(path,id)`, allowing equal hash:range IDs in distinct identical-content files.
Symbol IDs identify same-file declaration ranges, qualified by the unit path.
Foreign gaps carry their own path/hash and referencer ranges. The bridge checks
canonical confinement, unit/symbol provenance, consistent per-path hashes, source
length/order/accounting and configuration metadata.

Named/default imports and proven named/star/local/default reexports preserve
original import/export route units before admitting the implementation. Routes
track both requested export name and semantic symbol identity; aliases do not
consume extra semantic depth. Cycles terminate without pretending they prove a
route. Ambiguous export modules, missing exports and unsupported namespace/foreign
property dispatch produce gaps without inferred endpoints. Declaration-only or
ambient runtime targets are omitted; overload implementation bodies and intentional
interface/type context remain supported. Constructors, fields and runtime state
retain the Phase18 partial-coverage policy.

Every filesystem operation confines canonical paths, including config extends,
directory traversal, module metadata, source loading, references and symlink
origins. Package implementations are blocked before compiler source loading,
including in-repository node_modules symlinks and triple-slash references.
Declarations may inform static resolution but are not implementation context.
Callers, ambient globals, libraries and separate referenced projects remain gaps;
module side effects are reported and never executed.

Emission retains whole-unit BFS depth/source budgeting, separate from model and
render budgets. Import/reexport/target units share referrer depth+1; a missing or
omitted route stops that expansion. Graph loading independently caps64 unique source
attempts (including failures),1,000,000 admitted foreign UTF16 units and
4,000,000 cumulative foreign bytes charged before reading.
Selected-source processing remains subject to the bridge's bounded subprocess
timeout. Resource refusal is an explicit source-load gap, not no dependencies.

Tests-first evidence:10 initial Node cases failed for the absent API; Python
collection failed for the absent bridge. Additional reproducing route-name,
default/local export, cycle, missing/ambiguous export, package-origin, implicit
modern-mode, ambient declaration and snapshot-consistency cases failed before
repairs. Failed oversized/parse-error source attempts also consume graph resource
budgets; instrumented read-count regressions failed before this accounting repair. Positive controls retain valid aliases, duplicate-star targets, explicit
disambiguation, overload bodies and interface/type context. Fixtures also cover
relative/path imports, shared/cyclic/identical files, CRLF/astral fidelity, exact
whole-unit/depth budgets, config hashes, missing/broken configs/modules, parser
failure, boundary escapes, inherited/dynamic gaps and instrumented zero package
implementation reads. Existing tests are retained; bridge validation is shared
without changing local contracts.

Environment: Python3.12.14/pytest9.2.0, Node24.22.1/TypeScript5.9.3.
Baseline: fresh build/typecheck, Node26/26 and Python395/395 passed101.39s,
zero failures/skips/xfail. Focused:24 project Node and29 project/local Python
passed15.11s before the final parser/resource cases. Final implementer gate:
fresh build/typecheck, Node53/53 and Python408/408 passed101.75s, zero failures/
skips/xfail; git diff --check clean. Independent verification reviewed the complete
diff and outgoing documents, then reran fresh build/typecheck, Node53/53 and
Python408/408 in102.88s, zero failures/skips/xfail; git diff --check clean.
The final resource accounting repair was separately reviewed; no blocker remains.
Evidence date:2026-10-29. Synthetic fixtures; accumulated Laya tests mock only
the SDK boundary. No actual model/SDK/Claude execution or activation. Explanation
quality, universal dependency sufficiency and live compatibility remain unverified.
Verifier verdict: VERIFIED for Phase19A helper/bridge scope.
Decision: COMPLETE for19A; project flow/hook integration remains pending.
