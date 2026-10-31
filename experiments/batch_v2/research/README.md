# Experiment research helpers

Track A implementation, isolated from production. No real task, new cases, campaign or live calls. [Verification and pending checks](../docs/track-a-verification.md).

Run commands from `experiments/batch_v2/`. `development`, `temperature` and `policy` each load only that exact role. IDs are filtered before opening checkpoints/inferences; overall runner summaries are never selection inputs. Final reports require a frozen-finalists artifact and evaluate only its exact settings and gates. Sealed files are an operational separation, not access control against deliberately opening them.

## Interfaces and conventions

- `scores.py`, `metrics.py`: pure standard-library scores, DOCTOR, optional real-logit margin; confusion/support/recall, present-class balanced accuracy, canonical-class macro F1, multiclass MCC, NLL, Brier **sum**, four gate cells, gate MCC and **grouped-step AURC**. Zero-denominator MCC returns zero with a flag; empty metrics and zero-acceptance risk are unavailable. Strict NLL infinity uses JSON `null` plus `infinite_zero_probability`, separate from clipped diagnostics. Original probabilities remain unchanged, normalization corrections up to 0.001 are disclosed, and zero origin is unknown unless separately verified.
- `records.py`, `protocol.py`: frozen source-family roles, hashes, checkpoint/inference integrity and cumulative round compatibility. Model asset content/size identities are independent of config IDs; aliases are not silently unified.
- `temperature.py`: initial supported grid; adjacent tied-region refinements; 0.1 then 0.02 steps; NLL/Brier tolerance 0.001; maximum three refinements. Default is never numeric. `curves_from_evidence` enforces complete equal support. Supply rounds chronologically: repeated authored baseline calls retain original source evidence and list fresh repeats as excluded diagnostics; other repeats require a future explicit protocol. Stops carry all tested contenders forward. Requested settings are not proof of effective settings.
- `policies.py`, `analyze.py`: tied scalar and AND sweeps/frontiers, attained 25/50/75/90/100% coverage and <=1/2/5% empirical risk views; class/noise/tag gate denominators, source-family paired bootstrap (seed 1729, 2,000 samples). Multi-candidate intervals are descriptive. Incomplete probability evidence cannot silently reduce policy selection denominators. Experimental results stay separate from exact native replay. HTML exposes groups, policies and paired uncertainty.
- `next_round.py`: conservative Q0/BA/MCC/critical-group/native-trade-off retention, paired pruning only outside 0.02 tolerances with five families and full class support. Unresolved alternatives remain. Unsettled cases have operational outcomes, without invented labels. Proposed suites pass actual RV2 validation; no model invocation. Numbered records are immutable; journals append using existing templates.
- `export.py`: compact evidence/recipes, inventories and hashes, separate full raw archives, operator-attested durable references. Local-only exports are incomplete; supplied references do not verify recipient access.

## Sidecars and Python controller API

`calibration_roles.json` maps **every** source-family ID to one of `development`, `temperature`, `policy`, `held_out`. The middle two require RV2 `split=calibration`; unknown families and mismatches fail. Do not insert sidecar fields into strict RV2 inputs.

The protocol has `campaign_id`, canonical `cases_hash`, exact-byte `case_file_sha256`, `roles_hash`, `critical_groups`; optional `question_tolerance`, `bootstrap_seed`, `bootstrap_samples`, `supported_range`, zero-based `refinement_number` and `temperature_settings`. Freeze these before a campaign. Call `validate_protocol(..., cases_path=...)` to verify exact input bytes. No helper mutates cases.

Python APIs: `read_run`, `curves_from_evidence`, `decide`, `write_round`, `persist_finalists`. `decide` consumes permitted development evidence and optional chronological temperature evidence, checks their shared identity, and emits a completed next-run decision plus a runner-compatible suite. `write_round` refuses overwriting and appends journal/current-status updates.

Finalist keys are `question_id|config_id`. Definitions contain exact `question`, `config`, and `policies` with stable `id`, `kind` (`native` plus exact `rule`, or `experimental` plus `conditions`). Freezing requires complete policy-calibration evidence, Q0 and a protocol hash; it validates native replay and binds definitions/evidence by hash. Final analysis applies those frozen gates without sweeping.

## Exercised offline commands

```bash
python -B -m unittest discover -s checks -v
python -B checks/demo_research.py --output checks/output/research-demo --source-commit COMMIT
python -B -m research analyze --run RUN --roles ROLES --stage development --output REPORT
python -B -m research export --run RUN --roles ROLES --stage development --output COMPACT --sealed-output SEALED --source-commit COMMIT
python -B -m research mark-published --output COMPACT --compact-reference DURABLE_COMPACT --sealed-reference DURABLE_SEALED
```

Final stage additionally requires `--finalists FILE`. The export Python API accepts `protocol`, `decision_history` and `frozen_references`; include exact frozen inputs or retrievable references in real decision handoffs. The demo reuses only existing mechanical fixtures and is not a real campaign.

## Pending Mac probe

`python -B -m research.probe --help` describes the opt-in interface check. It accepts existing case/suite paths, a JSON temperature list, hard `--max-calls`, immutable `--output` and explicit `--allow-live`. It refuses non-Mac live operation, uses installed assets, never installs/upgrades SDK/model packages, and checkpoints actual prediction attempts before each call plus observations afterward. It was **not** run here.

Ordinary returned probabilities select the sufficient live-matrix route. Optional offline routes require explicit precision/T0 verification references plus parity at two distinct temperatures within recorded tolerance. Synthetic parity does not verify a live route. Effective temperature remains unavailable at the current SDK boundary.
