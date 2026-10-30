# Reviewed audit fixes

Implemented on top of 00db206cae46fa508bba3fe62c11c57c95df4668 using Sharon's
V1 decisions in audit-fix-plan.md. Tests were committed before the four fixes.

## Resulting behavior

- Object shorthand resolves its actual value binding, including imports, while
  preserving shadowing, deduplication, depth and source-size budgets.
- Identical candidate signatures return ambiguous_candidates before loading LAYA.
  LCR emits no additional context; Claude handles the original prompt normally.
- The default filename pattern collects every complete .ts path in prompt order.
  Member access, decimals, .tsx and .ts.bak are ignored. FileReference metadata,
  duplicates, custom patterns and separate flow eligibility are preserved.
- Referenced bodyless/ambient repository .ts declarations remain useful context
  with declaration_only gaps. Implemented overloads avoid false gaps. Existing
  package and .d.ts read restrictions remain unchanged.

## Scope retained

Three cases remain explicitly skipped: one concurrent symlink replacement and
two duplicate-key rejection cases. Configuration authoring guidance explains
unique keys and condition arrays. The singleton choice gap is excluded from the
active fixes; huge-number and Unicode formatting changes remain outside this work.

## Verification

The helper build and all 61 Node tests passed. Targeted dependency Python checks
passed (65 cases). Additional real-hook subprocess checks using a fake SDK
confirmed declaration text/gaps and the ambiguity no-op. Astra implemented and
reviewed the reasoning-sensitive dependency changes and independently reviewed
the default regex and ambiguity handling.

Full Python suite: **455 passed, 3 skipped** in 119.62 seconds.
The earlier exploratory
full run started before the new helper build and therefore is not final evidence.
No real LAYA/Claude accuracy or token-savings measurement was performed.

## Review notes

Existing method-selection test fixtures now give same-named functions different
signatures so their confidence, budget and mapping checks still exercise model
selection. New class/object tests cover indistinguishable signatures explicitly.
An old .tsx flow assertion now expects no_file rather than excluded, consistent
with the agreed .ts-only default extraction; both paths remain no-ops. The old
project ambient-declaration expectation was updated to retain its signature.

The original audit report and ZIP are historical evidence and have not been
rewritten to represent these fixes or Sharon's later scope decisions.
