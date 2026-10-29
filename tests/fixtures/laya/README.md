# Supplied examples

`captured-request.json` was extracted with `ast.literal_eval` from the supplied
`step2_multi.py` without executing it. `captured-raw.json` is the unchanged supplied
`step2_multi.json`. The user identifies these as a real request/response example.
They cover five questions and choice, noul and score. SDK version, revision and
capture date are unknown. The requested checkpoint is `aac6fef/laya-mlx`; the raw
response's `model` field is `laya-rl-agent`, a response label whose relationship to
checkpoint identity has not been verified. It is not checkpoint metadata evidence.
The existing source default remains `aac6fef/laya-typed-decisions-mlx`.

`choice-*` is a derived single-question subset, retaining every department answer
field and original top-level fields. It is not a separately captured call.
No sensitive source text was present and no text sanitization was applied.
The fruit response in the direct example is explicitly synthetic.

`enriched-original.json` is a separate downstream parity snapshot produced by
executing only the original pure `enrich.py` helper (no runner/SDK import), SHA256
`efc9720c9b78aa27222373be0d23ef2764fa6949534f5aa108d84668f7f6c012`.
It is never sent to the model and does not replace the raw capture. Numeric unit
tests also use independently calculated expected gap/entropy/distance values.
