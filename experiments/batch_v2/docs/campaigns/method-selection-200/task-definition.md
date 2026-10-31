## 3. Freeze the task boundary

For this first campaign, the request asks to **explain** callable code. Select one supplied callable only when the request identifies exactly one appropriate target from the visible names and signatures. Otherwise return no selection.

This matches the current question text. The first flow also admits `generate_tests`, but the current method-selection wording says “explain.” Test-generation requests need a separate scope decision and subsequent campaign; success here does not establish their accuracy. Modification requests are also outside this campaign.

Only names, signatures, and request text are model evidence. No method bodies, docstrings, imports, call graphs, hidden author knowledge, expected answers, notes, tags, or split labels enter inference. A case requiring the implementation body to resolve the target belongs in the insufficient-information group.

Boundary policies:

| Request situation | Expected method answer | Expected multiple answer | Expected final selection |
| --- | --- | --- | --- |
| Exactly one identifiable target | Its generated readable label | `no` | That callable's ID |
| Requested callable absent | `none_or_unclear` | `no` | None |
| Singular target cannot be distinguished from the supplied signatures | `none_or_unclear` | `no` | None |
| Explicitly asks to explain two or more supplied callables | `none_or_unclear` | `yes` | None |

Mentioning a second method as background or explicitly excluding it does not make the request multi-method. “Explain A; ignore B” targets A. “Explain A and B” targets neither individually. Avoid unresolved mixed-intent cases that would require a new precedence policy.

For a genuine multi-method request, the final no-selection result is correct even if the raw method answer is a concrete method and the multiple-method guard blocks it. Report the raw method error separately; do not erase the guard's contribution.

## 4. Actual input and output structure

The public V2 input is:

```python
{
    "text": "Explain how calculateInvoiceTotal computes the total.",
    "source_outline": full_validated_typescript_outline
}
```

Generate outlines once from small checked-in TypeScript fixtures using the real outline utility. Preserve schema version, path, source hash, callable IDs, signatures, ranges, locations, diagnostics and limitations. Do not invent abbreviated outlines or fabricate identity fields. Validate fixtures before freezing the campaign; the block itself does not read source files.

The block prepares model criteria such as:

```json
{
  "calculateInvoiceTotal": "export function calculateInvoiceTotal(invoice: Invoice): number",
  "calculateInvoiceTotalWithAdjustment": "export function calculateInvoiceTotalWithAdjustment(invoice: Invoice, adjustment: number): number",
  "none_or_unclear": "No single matching callable, or unclear request."
}
```

Unique names become labels. Repeated names with distinct signatures use `name@line:column`; a real callable named `none_or_unclear` is disambiguated too. Private `candidate_map` and `label_map` retain source identity outside the model payload. Candidate order remains fixed for each input across every configuration.

A selection requires an accepted concrete `method` answer and an accepted `multiple_relevant=no`. The output contains `selected_id`, `reason`, both maps, and the two decisions. Capture `data.reason` as the domain outcome; a completed block can still refuse selection.

Empty candidates, repeated identical signatures, more than 64 candidates, or an input above the 16,000-character default are pre-inference skips. Test those mechanically outside the 200 inference inputs. Require all 200 cases to reach prediction under both wordings without truncation. Count limits in Unicode characters exactly as the block does, not in tokens.

