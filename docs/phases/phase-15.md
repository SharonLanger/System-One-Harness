# Phase 15 — prompt hook protocol

Starting commit 01a29ac69a2a53d0ade128fea2f150723e2a930e. Independent planner and
reviewer `/root/flow_builder/phase_reviews` (Luna medium). Baseline fresh build,
6 Node and 290 Python tests passed. Same Python 3.12 / Node 24 / TypeScript 5.9.3 environment.

Official unversioned https://code.claude.com/docs/en/hooks verified 2026-10-29 by
implementer and planner: UserPromptSubmit command receives stdin JSON; prompt,
cwd and event identify this adapter's required input. Exit 0 hookSpecificOutput
with hookEventName and additionalContext adds context; empty stdout is no-op.
Exit 2 blocks, so argument errors are normalized to 0. No block or prompt rewriting
fields emitted. Current docs describe a 10,000-character context spooling threshold;
our lower 8,000-character ceiling rejects oversized context rather than truncating.
Actual Claude version/delivery remains unverified; no harness installed/activated.

Scope: only hooks/user_prompt_submit.py as adapter, with CLI explicit absolute
--repository-root, optional existing --config JSON and opt-in --real (live support
unverified). Omitted --real always safe no-op without SDK import. No runtime fake
mode. POSIX SIGALRM bounds stdin/source/Python SDK path to 10s by default, configurable
>0 and <=300 (finite). Helper retains its 5s subprocess timeout. Input max 65,536 Unicode
characters; additionalContext max 8,000 (lower configurable). Budgets refuse, never
truncate. Input must be object with exact expected event; other event silently
no-ops. Cwd must exist inside explicit canonical root. Pipeline Python stdout is
redirected to stderr; hook stdout is exactly one protocol object or empty. Failures
and source/model no-ops diagnose on stderr, exit 0. No settings/session files changed.

Independent planned checks: subprocess realistic stdin/output, nested cwd, exact
SDK model/settings/request, prompt/source preservation, noise redirected, invalid
JSON/fields/CLI/config/root, noneligible/unsupported events, explicit model gate,
model/source failures, bounded sleep, input/context exact budgets and no truncation.
Tests inject fake laya_mlx through child-only sitecustomize, with independently
specified exact requests/raw responses; production parser, adapter, questions,
enrichment, rules, flow and extraction execute. No SDK/MLX import, installation,
weights or real inference. Fake model mock-hook(.2/fr), exact kwargs asserted;
requested settings are simulated, not actual model metadata. Synthetic protocol
fixtures match current docs; model/policy schema provisional as earlier phases.

TDD: 30 new tests first failed (adapter absent), then 30 passed. Added five checks
(three missing-field parameters and two further tests), reaching 35. These missing-field,
duplicate-key, default output ceiling and no-SDK default checks, and explicit Bash
launch to strengthen the contract. Original tests unchanged. Known limits: POSIX
only; Python alarm cannot prove interruption of an uncooperative native SDK; true
live deadline/stdio compatibility remains Phase20. Runtime argv/startup failures
before Python starts are outside adapter handling. Signature fallback remains off.
First full candidate gate: fresh build/typecheck, 6 Node +325 Python passed
(59.26s Python), no skips/xfail. Before commit, root requested Astra high design
review of the 20s ceiling for future cold model loads. Astra independently found
no measurement justifying 20s; a fresh process imports/loads/inferences in the same
budget. Adopted explicit bounded max 300s while keeping default 10s and helper 5s.
This is an administrative ceiling, not observed model latency. Outer harness
must exceed internal deadline plus grace (example 5s); default harness 30s is not
enough for larger explicit budgets. Python official signal docs (checked by Astra,
https://docs.python.org/3/library/signal.html) confirm native C may delay handlers;
no hard live cancellation guarantee. Actual cold/load/inference/cancellation
measurements remain a Phase20 gate. Added planned 21/300 fast success tests (both
red against old ceiling), invalid finite/nonfinite/over-cap and context budgets;
kept original sleep/deadline assertion unchanged. Eleven new budget parameter cases
(including two expected reds at 21/300) bring hook tests to 46; other new checks
document existing validation and passed immediately. Final implementer fresh
build/typecheck +6 Node +336 Python passed in 55.02s, zero skips/xfail. Final
independent sequential fresh build/typecheck +6 Node +336 Python passed
(56.16s Python), zero skips/xfail. Reviewer inspected actual hook, all 46 cases,
docs and requirements. Verdict: VERIFIED for stated mock protocol scope.
Decision: COMPLETE. Real compatibility blocked until Phase20.
