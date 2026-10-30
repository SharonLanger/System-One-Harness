# Runnable experiments: first increment

Status: the choice experiment is implemented locally. No real Laya execution has
been verified. Noul and score are deferred to a later batch.

## Scope and delivery

The first deliverable is `experiments/laya_choice.py`, its static input JSON,
shared small `support.py`, and focused automated tests. Implement `laya_noul.py`
and `laya_score.py` together in a later batch. Follow
[the experiment conventions](../experiments/README.md).

The choice script calls the existing Laya adapter with real loading by default
when manually executed. It uses a trivial fruit choice. Keep the full definition
visible in its input file. Display raw results without enrichment or rule logic.
The later scripts will use a fruit-mentioned noul question and an explicit
small/large score question.

The choice script supports changing model, temperature, and language through its
input configuration and optional explicit command-line overrides. Model and
temperature are prominent in terminal output, summary, and JSON. Default uses
the existing checkpoint and SDK-default temperature. No additional real model
or numeric temperature is assumed compatible without supplied evidence.

The script exposes reusable `run(...)` and `main()` entry points. Provide
loader/registry injection for tests and future repetition. Share no global agent
cache. A small observer around the existing SDK boundary may retain a raw reply
before validation; it must not change arguments, responses, or invoke inference
twice. Label non-JSON diagnostics rather than presenting them as valid raw JSON.

No changes to production flows, block rules, model-setting semantics, or hook
activation are included. If implementation requires unsupported information,
record the gap. Do not manufacture intermediate results.

## Implementation sequence

1. Implement the output helper, choice experiment, input handling, and error
   reporting; update docs and add ignored results paths.
2. Run focused choice tests and the repository checks appropriate to that change.
3. Commit the choice experiment as the first small commit. Add noul and score in
   a later batch after this script has been tried on Sharon's Mac.

The planning documents alone do not constitute completion of this increment.

## Required tests

- Each implemented script uses the production adapter with injected synthetic SDK
  responses in tests; importing scripts does not import/load real Laya.
- Static question definitions reach prediction unchanged, and raw responses are
  retained. Each question type displays its actual values without semantic
  answer assertions or invented acceptance rules.
- Model, null temperature, explicit temperature, and language are forwarded
  exactly through existing RunConfig behavior. CLI/input precedence is explicit.
- Metadata distinguishes requested values from observed values and unknowns.
- Same configuration reuses its object within a supplied registry; different
  configuration creates a separate object; independent invocations are fresh.
- Arbitrary working directory execution finds its input and intended output.
- Script-stem result folders, readable date/time, timezone metadata, collision
  handling, and no overwrite. Summary and JSON describe the same run.
- Loader failure, prediction failure, malformed response, invalid input, and
  output-write failure produce truthful diagnostics and nonzero status; retain
  evidence where possible and never switch to mocks automatically.
- A surprising but valid model response remains a successful technical run.
- No production-flow behavior changes, source edits by experiments, or hook
  activation. Existing tests are preserved.

Run the repository's accumulated checks on the final implementation candidate:

```bash
npm --prefix typescript-helper run build
npm --prefix typescript-helper test
python -m pytest -q
git diff --check
```

These checks mock the SDK on this host. Sharon's manual runs provide real Mac
evidence; mocked success must never be reported as real compatibility.

## Subsequent increments, after feedback

First extend direct calls with multiple questions and explicit model/settings
comparison. Then add existing building-block and flow entry points, including a
bad-method no-op and a controlled technical error. Next add saved-hook replay.
Finally add bounded repetition and aggregation after deciding the desired batch
input/report format. Actual Claude end-to-end verification remains separate.
