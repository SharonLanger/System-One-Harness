# Final decision: <campaign-id>

Status: not evaluated. Complete only after finalists are frozen.

## Frozen finalists

- Freeze time and artifact hash:
- Selection evidence roles and records:
- Selected configuration IDs and unchanged reference:
- Exact question, ordered choices and semantics:
- Exact rule/cutoff and expected abstention behavior:
- Model and requested/known effective settings:
- Input-rendering contract and length policy:

## Held-out evidence

- Dataset version, family-role hash and held-out case count:
- Run IDs, source/runtime versions and shared evidence:
- Label metrics, calibration, coverage/error and per-class/tag results:
- Paired differences and uncertainty:
- Technical failures, unsupported metrics and limitations:

## Outcome

- Best tested candidate / tied candidates / inconclusive / no useful improvement:
- Why this outcome follows from evidence:
- Trade-off retained and any deployment preference still undecided:
- Regression cases and known unsupported requests:
- Whether new experiments are needed:

## Building-block handoff

- Behavior the block must implement:
- Exact evaluated payload and label/rule contract:
- Pure experiment helpers considered for separate promotion:
- Required payload, output, truncation and rule parity checks:
- Production implementation scope and tests:
- Evidence required if runtime/preparation changes:

This record supports a later building-block implementation. It does not itself merge or deploy code. If held-out failures guide a revised design, mark that dataset as development evidence and reserve new held-out data for a later final claim.
