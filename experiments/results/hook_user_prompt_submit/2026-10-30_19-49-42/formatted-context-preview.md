# Formatted context preview

Rendered from the saved inventory extraction with the new formatter. This is a preview, not a new hook or model run. Original run artifacts are unchanged.

Formatted context: 1,184 characters (previous raw payload: 8,958).

Selected TypeScript context (partial).

## Selected method

/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts (lines 46–56)
```typescript
export function consolidateOrderLines(lines: readonly OrderLine[]): OrderLine[] {
  const quantities = new Map<string, number>();
  for (const line of lines) {
    const sku = line.sku.trim();
    if (!sku || !Number.isInteger(line.quantity) || line.quantity <= 0) {
      throw new Error('Order lines require a SKU and positive whole quantity');
    }
    quantities.set(sku, (quantities.get(sku) ?? 0) + line.quantity);
  }
  return Array.from(quantities, ([sku, quantity]) => ({ sku, quantity }));
}
```

## Supporting declarations

/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts (lines 9–12)
```typescript
export interface OrderLine {
  sku: string;
  quantity: number;
}
```

## Context notes

- Module initialization and side effects are not reconstructed.
- Callers and ambient context are not exhaustively collected.
- Some references have no resolved supporting declaration.
