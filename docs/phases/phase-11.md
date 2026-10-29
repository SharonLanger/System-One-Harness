# Phase 11 — exact callable source

Objective: retrieve exact supported callable text with source provenance.
Starting published commit:1615ab1 (Phase10), clean. Baseline build/typecheck,
all4 Node tests and237 Python tests passed. Python3.12.14/pytest9.2.0,
Node24.22.1, TypeScript5.9.3; SDK/harness unused.
Independent planner/final verifier: /root/source_builder/phase_reviews
(gpt-6-luna/medium); test plan delivered before implementation.

Plan: LF/CRLF source equality; astral Unicode before/inside; attached/interior/
trailing comment boundaries; same names in separate files; empty body; unknown/
stale/outdated IDs and source changes; unsupported class/arrow diagnostics;
malformed extraction responses; real bridge; unchanged source bytes.
Expected raw source manually written in tests; Node additionally compares exact
original source.slice(start,end). No previous expectations/fixtures weakened.

Contract: extract_callable(path,id) dispatches JSON extract request. Helper reads
one source snapshot for outline/hash/slice. ID must match a currently supported
candidate, including SHA256 of decoded UTF8 source and UTF16 start/end. Raw `code`
is exact JavaScript slice; Python never indexes source using UTF16 offsets.
`callable`, canonical path/hash, diagnostics and limitations preserve provenance.
Leading attached comments excluded (`getStart` first token); body comments retained;
trailing comments excluded (`getEnd` exclusive). Separate display_code prefixes
1-based source lines and normalizes display line endings to LF; raw code retains
LF/CRLF. No source writes. Broader forms/dependencies remain deferred.

Official source/docs checked2026-10-29: Microsoft TypeScript Architectural Overview
(https://github.com/microsoft/TypeScript/wiki/Architectural-Overview) documents
getStart token boundary versus getFullStart trivia. Compiler source Node/SourceFile
interfaces document UTF16 line/position units; actual pinned compiler and astral
fixtures provide executable evidence. Earlier compiler API reference retained.

TDD red: Python import extract_callable missing; two new Node extraction tests
failed `extractCallable is not a function` while4 previous tests passed. Initial
implementation compile blocker TS2352 (CLI request id narrowing) sent to heavy
repair agent /root/source_builder/source_repairs (gpt-6-astra/high).
Heavy repair moved id validation into the narrowed extract dispatch branch,
removing the cast. Reproduced TS2352 then fixed; no protocol expansion. Heavy agent
ran build +6 Node +243 Python tests. Implementer independently repeated:
npm --prefix typescript-helper run build; npm --prefix typescript-helper test;
python -m pytest -q:6 Node and243 Python passed,0 failed/skipped; diff check clean.
Independent reviewer inspected complete requirement/source/tests/diff and reran
build/typecheck, all6 Node tests and243 Python tests:0 failed/skipped. Exact
fidelity/provenance and inherited contracts confirmed; no blockers.

Execution mode: inherited SDK boundary mocked; source parser/bridge/extraction
are real. No SDK import/weights/model calls; no new model/settings combinations.
Inherited JSON/enrichment/rules/answer tests retained. Real compatibility deferred
until Phase20. Files: TS helper/CLI, Python bridge, new Node/Python tests, README,
progress and phase record. Evidence date:2026-10-29.
Verifier verdict:VERIFIED for Phase11 scope. Decision:COMPLETE.
