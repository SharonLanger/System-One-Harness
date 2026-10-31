# Connected TypeScript fixture

The existing billing fixture is accompanied by five deterministic production files in `src/fulfillment`. These files need no external packages and use the fixture's strict ES2020 TypeScript configuration.

- `inventory.ts`: five functions for stock validation, SKU lookup, availability, line consolidation, and reservation snapshots.
- `packing.ts`: five static methods for unit counts, weight, parcel packing, billable weight, and summaries.
- `pricing.ts`: five functions for rate validation, merchandise value, freight, insurance, and quotes.
- `shipment-service.ts`: five instance methods implementing `ShipmentOperations`: availability, reservation, planning, quoting, and descriptions.
- `reporting.ts`: five functions for report rows, complete reports, charge totals, summaries, and manifests.

The `ShipmentService` constructor is additional to the 25 implemented named functions and methods. Interface method declarations are not counted.

## Call links

- `reporting.buildShippingReport` calls `buildShippingReportRow`, which calls the five-method `ShipmentOperations` abstraction through four of its methods.
- `ShipmentService.describe` calls availability, quote, and `PackingCalculator.packingSummary`; its quote calls parcel planning and `pricing.quoteOrderShipping`.
- `ShipmentService.reserve` calls availability and `inventory.reserveOrderStock`, returning updated copies without mutating its input stock.
- `pricing.quoteOrderShipping` calls parcel building, merchandise valuation, freight charging, and insurance charging.
- `PackingCalculator` calls inventory consolidation and SKU lookup; pricing also calls inventory consolidation and lookup.
- `inventory.reserveOrderStock` calls consolidation, lookup, and availability; availability and lookup call stock validation.
- `renderShippingManifest` calls report summarization, which calls `totalShippingCharges`.

Stock records use unique exact SKUs; order SKUs are trimmed. Monetary values are rounded to cents. Reservation results are snapshots: create a new service from the returned stock to represent a later reservation state. Report readiness is evaluated independently against the service's stock snapshot; reports do not allocate stock across orders. Parcel building preserves consolidated order order and uses the current parcel until the next unit would exceed capacity.

## Suggested single-method experiment prompts

- Extract only `ShipmentService.describe`, including its cross-file call context.
- Explain only `PackingCalculator.buildParcels` and identify its inventory dependencies.
- Refactor only `quoteOrderShipping` while preserving freight and insurance behavior.
- Review only `reserveOrderStock` for validation and input mutation behavior.
- Inspect `buildShippingReportRow` and its calls through `ShipmentOperations`.
- Explain only `renderShippingManifest` and its summary formatting dependencies.

This fixture expansion adds production examples only; it does not add or change tests.

These suggestions describe possible tasks; the existing hook flow only accepts
the `Explain \`path.ts\`: question` format. Ready events in
`experiments/inputs/hook_inventory.json`, `hook_packing.json`, `hook_pricing.json`,
`hook_shipment.json`, and `hook_reporting.json` use that format. For example:

```bash
python experiments/hook_user_prompt_submit.py --input experiments/inputs/hook_inventory.json --deadline 120
```

Inline callbacks are intentionally present: they should not become standalone
outline candidates. Calls through the injected `ShipmentOperations` interface
are deliberately not proof of a particular runtime implementation; the helper
can report unresolved dispatch. Use the inventory example first for a simple
selection; deeper service examples may encounter context limits or dependency
gaps. The fixture is parsed as source, not executed by the hook.

## First-flow fixture provenance

Copied from `experiments/fixtures/connected_project/` at upstream commit
`223b83b90c7c8f3b397c17f80f48908b579a8556`. Source tree, imports and tsconfig
are unchanged. First-flow tests use temporary copies of this test-owned fixture.
