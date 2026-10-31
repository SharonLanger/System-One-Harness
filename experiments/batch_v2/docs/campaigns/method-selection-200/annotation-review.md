# Annotation review

Ground truth was authored from request text and visible method names/signatures before any LAYA predictions. The generated annotation-review.json records a per-case rationale. This is author self-review, not independent annotation review.

Single-target requests select the named/signature-identifiable callable. Absent or unresolved singular targets expect none_or_unclear and multiple=no. Explicit requests for two methods expect none_or_unclear and multiple=yes; either guard refusing final selection is correct at block level.

A second mechanical pass validates each expected label against actual compiler-produced criteria, maps concrete targets to source IDs, checks identical candidate sets across question wordings, and enforces family split integrity. This verifies consistency, not semantic annotation independence. Independent review remains outstanding before treating results as a final benchmark.

All scenarios are synthetic. Method bodies are placeholder implementations and are never sent to the classifier; behavioral descriptions refer to names/signatures only. Category and noise strata deliberately overrepresent difficult requests.
