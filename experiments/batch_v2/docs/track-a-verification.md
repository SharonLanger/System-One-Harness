# Track A implementation evidence

Status: implementation ready for review; **not ready for a live campaign**. No new real use case, cases or campaign was defined. Production and the existing RV2 schemas/engine/reports remain unchanged.

## Completed mechanical verification

- `python -B -m unittest discover -s experiments/batch_v2/checks -v`: **30 tests passed**, comprising 16 existing RV2 regressions and 14 research test groups. Astra independently ran all 30 successfully and approved implementation review readiness after the default-temperature carry regression.
- Golden majority 90/10, perfect/inverted/multiclass confusion, degenerate/empty/class-absent metrics, strict-zero NLL, sum Brier, DOCTOR, tied AURC and all four gate patterns pass.
- Provenance mutation, missing inference, held-out checkpoint open trap, role exclusivity, model asset/config-ID normalization, cumulative identity, incomplete selection denominators and exact frozen gate tests pass.
- Broad→refined→combined→fine proposals, repeated baseline exclusion provenance, cross-campaign rejection, flat/tied/boundary/cap stopping, SDK-default carry with numeric baseline, unsettled operational cases and missing final channels pass.
- Proposed suite JSON passes the actual RV2 schema/runtime validator; direct/replay parity and annotation isolation pass the existing RV2 checks. No SDK/model package was installed or upgraded.
- Exercised `python -B checks/demo_research.py`, `python -B -m research analyze`, `export`, `mark-published`, and `python -B -m research.probe --help` from the runner directory. See [mechanical demo](../checks/fixtures/research-demo/README.md).
- Static HTML checks confirm viewport/wrapping and exposed group/policy/paired sections. This is not browser acceptance.

## Pending environment checks

Mac live interface probe/parity: **not run** in this Linux environment. The opt-in counted probe is implemented and ordinary live temperature matrices remain the sufficient fallback. Requested settings are not proof of effective settings. Optional offline routes remain unverified until a Mac report records precision/T0 evidence and parity at distinct settings.

Browser acceptance, including the outstanding PR #21 report check: **pending**. `node checks/browser-check.cjs RUN_FOLDER` failed because installed Playwright lacked `chromium_headless_shell-1234`. A test-browser-only install via the bundled `playwright/cli.js install chromium` failed downloading a truncated/non-ZIP browser archive. No browser rendering/filter behavior is claimed. Rerun the existing check at 390×844 and desktop with an available browser; inspect the new expandable research report too.

Machine-readable readiness: [track-a-readiness.json](track-a-readiness.json). Do not mark full Track A complete or start a live campaign based on fixture evidence. Implementation PR merge still requires Sharon's review/instruction.

## Astra consultation and recorded refinements

Sharon required Astra consultation on deviations/problems. Sol consulted `gpt-6-astra` throughout and implemented its review corrections:

1. Linux cannot satisfy Mac evidence; keep campaign readiness blocked. GitHub API transport is acceptable when preserving the exact main base tree and scoped fast-forward commits.
2. Normalize config-keyed model fingerprints by model asset content/size, retain requested/effective/inference provenance, enforce cumulative questions/data/roles/source/adapter/runtime/rule-mode identities.
3. Validate deterministic checkpoint hashes/source IDs/config/status. Separate missing/invalid optional score channels. Disallow silent reduced probability denominators.
4. Freeze exact definitions with Q0 and complete policy evidence; replay native gates; final evaluation never sweeps. Add paired uncertainty and group policy denominators.
5. Preflight probe outputs, increment/persist actual predict attempts and save each observation; require distinct offline parity settings and explicit precision/T0 evidence.
6. Preserve original baseline evidence across rounds, list fresh repeats as excluded diagnostics; reject cross-campaign refinement, retain intentionally unsettled inputs operationally, carry unresolved tested temperatures (including SDK default) when stopping.
7. Include role maps, full definitions/recipes, helper hashes, original inventories and separate raw archives in exports. Publication remains operator-attested.
8. Astra approved browser-runtime unavailability as a review limitation only, with acceptance left pending. Final assessment: implementation PR may open; no live-readiness or merge authorization implied.

No cases were generated and no live model calls occurred. Optional automatic offline fitting remains deferred as the plan permits; verified transformations are provided but not enabled without live proof.
