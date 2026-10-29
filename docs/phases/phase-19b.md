# Phase 19B — project context through the complete prompt hook

Starting revision: Phase19A. Independent test planning and a separate design
review preceded implementation. Independent final verification is complete.

The flow now calls the project collector after accepted method selection, passing
the canonical repository root and existing dependency depth/source limits.
Selected ID, source hash, callable-map and confinement checks remain. Hook
protocol, flags, stdout isolation and final8,000-character ceiling are unchanged.
Direct local/extract APIs remain available; missing or unsupported configuration
retains exact selected/local source with explicit project gaps.

Model questions still contain only the original prompt and callable signatures.
Dependency source is collected after selection. Each foreign source is a coherent
collection-time snapshot; changing a dependency during selection can legitimately
produce its newer exact source/hash while the selected file remains unchanged.
No atomic repository epoch or complete caller/runtime coverage is claimed.

Synthetic subprocess cases use actual configuration parsing, path aliases,
multi-hop reexport routes, source collection, bridge, flow and hook. Only the
SDK boundary is simulated. Manually specified source units, independently
calculated file hashes and UTF16 slices verify foreign provenance and complete
selected code with CRLF/astral text. Caller, missing-module and module-effect gaps
survive serialization; an absolute side-effect marker never appears, and source
files remain unchanged. Signature-only request checks and single-call logging
remain active.

A9,000-character foreign constant behind a reexport fits the default dependency
collection budget but overflows final rendering and emits the documented no-op.
An explicit100-unit source budget instead includes complete route statements,
omits the oversized endpoint with a size gap, and delivers complete selected
code below the final ceiling. No render-time retry, truncation or offload occurs.
Further hook cases exercise exact/one-short full Unicode rendered budgets with
CRLF, reexports, unresolved references and all project metadata. Missing/implicit
modern configuration visibly falls back to local partial context. Existing local
budgets, malformed/stale source, fallback, abstention and stdout/no-op scenarios
remain in the full suite.

Tests-first: all7 new cases failed before flow integration. Existing expected-hook
rendering now uses project collection with the actual case repository root,
including tracked-source overrides. The malformed-collector monkeypatch targets
the new API. Existing assertions and regression scenarios are retained.
Implementation changes are limited to flow integration; the verified helper,
bridge and hook runtime are unchanged.

Environment: Python3.12.14/pytest9.2.0, Node24.22.1/TypeScript5.9.3.
Baseline: fresh build/typecheck, Node53/53 and Python408/408 passed107.57s,
zero failures/skips/xfail. Focused flow/hook gate:116/116 passed74.85s.
Final implementer gate: fresh build/typecheck, Node53/53 and Python415/415
passed116.40s, zero failures/skips/xfail; git diff --check clean. Independent
verification reviewed the complete diff and outgoing documents, then reran fresh
build/typecheck, Node53/53 and Python415/415 in112.86s, zero failures/skips/xfail;
git diff --check clean. No independent review blocker remains.
Evidence date:2026-10-29. All added fixtures synthetic; accumulated SDK execution
is mocked. No actual model/SDK/Claude execution or activation. Real compatibility
remains blocked until20. Classic/Node10 support and explicit modern-mode,
namespace/dispatch, declaration, module-effect, caller and resource gaps remain
as documented in19A. Explanation quality and universal sufficiency are unmeasured.
Verifier verdict: VERIFIED for the documented bounded Phase19 project/hook scope.
Decision: COMPLETE for Phase19.
