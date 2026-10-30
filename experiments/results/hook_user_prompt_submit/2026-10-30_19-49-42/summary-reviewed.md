> Re-rendered from the saved run. No hook or model was rerun; original summary, details, and trace are preserved.

# UserPromptSubmit replay

Outcome: **technical_error**. Exit code: 0. Hook PID: 68054.

No-op/error reason: laya hook noop: ValueError: context_budget_exceeded.

This runs the real hook subprocess. It does not install a hook in Claude.


## Hook output — what was actually returned

**No context was returned. stdout was empty.** The report's `null` is a missing parsed response; the hook did not send the JSON value `null` to Claude.

Rejection: **context_budget_exceeded**. Context size: **8958** characters; limit: **8000**.


### Prepared only — NOT SENT: complete hook JSON

This is the hook protocol envelope; `additionalContext` is the string added alongside the prompt.

```json
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "Selected TypeScript context (partial):\n{\"schema_version\":1,\"path\":\"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts\",\"source_hash\":\"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b\",\"diagnostics\":[],\"limitations\":[\"Runtime callable bodies are discovered recursively; destructuring-bound callable expressions remain unsupported.\",\"Locations and ranges use UTF-16 code units; comments before declarations are excluded.\",\"Bound expression signatures include their immediate binding header and transparent wrappers; raw code is only the callable expression.\",\"Type-only signatures are not runtime implementation candidates; computed names are source text, never evaluated.\",\"Project graph uses parsed Classic/Node10 resolution only; automatic libraries/types, ambient globals, separate referenced projects and callers remain partial.\",\"Only repository .ts source units are collected. Bodyless declarations are flagged; package implementations and .d.ts source units are omitted; project modules are never executed.\",\"Dependency graph loading is capped at64 unique source attempts,4,000,000 cumulative foreign pre-read bytes and1,000,000 admitted foreign UTF16 source units; selected source is governed by the subprocess deadline.\"],\"callable\":{\"id\":\"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b:1545:2047\",\"name\":\"consolidateOrderLines\",\"signature\":\"export function consolidateOrderLines(lines: readonly OrderLine[]): OrderLine[]\",\"start\":1545,\"end\":2047,\"location\":{\"line\":46,\"column\":1}},\"code\":\"export function consolidateOrderLines(lines: readonly OrderLine[]): OrderLine[] {\\n  const quantities = new Map<string, number>();\\n  for (const line of lines) {\\n    const sku = line.sku.trim();\\n    if (!sku || !Number.isInteger(line.quantity) || line.quantity <= 0) {\\n      throw new Error('Order lines require a SKU and positive whole quantity');\\n    }\\n    quantities.set(sku, (quantities.get(sku) ?? 0) + line.quantity);\\n  }\\n  return Array.from(quantities, ([sku, quantity]) => ({ sku, quantity }));\\n}\",\"display_code\":\"46: export function consolidateOrderLines(lines: readonly OrderLine[]): OrderLine[] {\\n47:   const quantities = new Map<string, number>();\\n48:   for (const line of lines) {\\n49:     const sku = line.sku.trim();\\n50:     if (!sku || !Number.isInteger(line.quantity) || line.quantity <= 0) {\\n51:       throw new Error('Order lines require a SKU and positive whole quantity');\\n52:     }\\n53:     quantities.set(sku, (quantities.get(sku) ?? 0) + line.quantity);\\n54:   }\\n55:   return Array.from(quantities, ([sku, quantity]) => ({ sku, quantity }));\\n56: }\",\"coverage\":\"partial\",\"dependencies\":[{\"id\":\"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b:129:194\",\"path\":\"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts\",\"source_hash\":\"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b\",\"start\":129,\"end\":194,\"location\":{\"line\":9,\"column\":1},\"kind\":\"InterfaceDeclaration\",\"code\":\"export interface OrderLine {\\n  sku: string;\\n  quantity: number;\\n}\",\"symbol_ids\":[\"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b:129:194\"]}],\"gaps\":[{\"code\":\"module_side_effects\",\"message\":\"Module initialization and side effects are not reconstructed or executed.\",\"start\":0,\"end\":2597,\"path\":\"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts\",\"source_hash\":\"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b\"},{\"code\":\"caller_coverage\",\"message\":\"Callers and ambient project/library context are not exhaustively analysed.\",\"start\":1545,\"end\":2047,\"path\":\"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts\",\"source_hash\":\"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b\"},{\"code\":\"unresolved_reference\",\"message\":\"No supported semantic declaration was found.\",\"start\":1652,\"end\":1655,\"path\":\"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts\",\"source_hash\":\"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b\"},{\"code\":\"unresolved_reference\",\"message\":\"No supported semantic declaration was found.\",\"start\":1726,\"end\":1729,\"path\":\"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts\",\"source_hash\":\"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b\"},{\"code\":\"unresolved_reference\",\"message\":\"No supported semantic declaration was found.\",\"start\":1730,\"end\":1734,\"path\":\"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts\",\"source_hash\":\"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b\"},{\"code\":\"unresolved_reference\",\"message\":\"No supported semantic declaration was found.\",\"start\":1755,\"end\":1761,\"path\":\"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts\",\"source_hash\":\"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b\"},{\"code\":\"unresolved_reference\",\"message\":\"No supported semantic declaration was found.\",\"start\":1762,\"end\":1771,\"path\":\"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts\",\"source_hash\":\"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b\"},{\"code\":\"unresolved_reference\",\"message\":\"No supported semantic declaration was found.\",\"start\":1777,\"end\":1785,\"path\":\"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts\",\"source_hash\":\"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b\"},{\"code\":\"unresolved_reference\",\"message\":\"No supported semantic declaration was found.\",\"start\":1795,\"end\":1803,\"path\":\"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts\",\"source_hash\":\"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b\"},{\"code\":\"unresolved_reference\",\"message\":\"No supported semantic declaration was found.\",\"start\":1828,\"end\":1833,\"path\":\"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts\",\"source_hash\":\"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b\"},{\"code\":\"unresolved_reference\",\"message\":\"No supported semantic declaration was found.\",\"start\":1913,\"end\":1916,\"path\":\"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts\",\"source_hash\":\"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b\"},{\"code\":\"unresolved_reference\",\"message\":\"No supported semantic declaration was found.\",\"start\":1934,\"end\":1937,\"path\":\"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts\",\"source_hash\":\"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b\"},{\"code\":\"unresolved_reference\",\"message\":\"No supported semantic declaration was found.\",\"start\":1956,\"end\":1964,\"path\":\"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts\",\"source_hash\":\"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b\"},{\"code\":\"unresolved_reference\",\"message\":\"No supported semantic declaration was found.\",\"start\":1980,\"end\":1985,\"path\":\"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts\",\"source_hash\":\"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b\"},{\"code\":\"unresolved_reference\",\"message\":\"No supported semantic declaration was found.\",\"start\":1986,\"end\":1990,\"path\":\"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts\",\"source_hash\":\"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b\"}],\"collection\":{\"max_depth\":2,\"max_dependency_chars\":12000,\"dependency_chars\":65},\"project\":{\"repository_root\":\"/Users/I337254/workspace/sharon-workspace/laya-context-router\",\"config_path\":\"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/tsconfig.json\",\"config_hash\":\"87139864318ec174310f4adce1aa1c7e0493763a6832b3410974764b983f4f4d\",\"config_sources\":[{\"path\":\"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/tsconfig.json\",\"source_hash\":\"87139864318ec174310f4adce1aa1c7e0493763a6832b3410974764b983f4f4d\"}]}}"
  }
}
```


### Prepared only — NOT SENT: additionalContext — exact text

The box contains only the 8,958-character string value, with no JSON-envelope escaping.

```text
Selected TypeScript context (partial):
{"schema_version":1,"path":"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts","source_hash":"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b","diagnostics":[],"limitations":["Runtime callable bodies are discovered recursively; destructuring-bound callable expressions remain unsupported.","Locations and ranges use UTF-16 code units; comments before declarations are excluded.","Bound expression signatures include their immediate binding header and transparent wrappers; raw code is only the callable expression.","Type-only signatures are not runtime implementation candidates; computed names are source text, never evaluated.","Project graph uses parsed Classic/Node10 resolution only; automatic libraries/types, ambient globals, separate referenced projects and callers remain partial.","Only repository .ts source units are collected. Bodyless declarations are flagged; package implementations and .d.ts source units are omitted; project modules are never executed.","Dependency graph loading is capped at64 unique source attempts,4,000,000 cumulative foreign pre-read bytes and1,000,000 admitted foreign UTF16 source units; selected source is governed by the subprocess deadline."],"callable":{"id":"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b:1545:2047","name":"consolidateOrderLines","signature":"export function consolidateOrderLines(lines: readonly OrderLine[]): OrderLine[]","start":1545,"end":2047,"location":{"line":46,"column":1}},"code":"export function consolidateOrderLines(lines: readonly OrderLine[]): OrderLine[] {\n  const quantities = new Map<string, number>();\n  for (const line of lines) {\n    const sku = line.sku.trim();\n    if (!sku || !Number.isInteger(line.quantity) || line.quantity <= 0) {\n      throw new Error('Order lines require a SKU and positive whole quantity');\n    }\n    quantities.set(sku, (quantities.get(sku) ?? 0) + line.quantity);\n  }\n  return Array.from(quantities, ([sku, quantity]) => ({ sku, quantity }));\n}","display_code":"46: export function consolidateOrderLines(lines: readonly OrderLine[]): OrderLine[] {\n47:   const quantities = new Map<string, number>();\n48:   for (const line of lines) {\n49:     const sku = line.sku.trim();\n50:     if (!sku || !Number.isInteger(line.quantity) || line.quantity <= 0) {\n51:       throw new Error('Order lines require a SKU and positive whole quantity');\n52:     }\n53:     quantities.set(sku, (quantities.get(sku) ?? 0) + line.quantity);\n54:   }\n55:   return Array.from(quantities, ([sku, quantity]) => ({ sku, quantity }));\n56: }","coverage":"partial","dependencies":[{"id":"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b:129:194","path":"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts","source_hash":"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b","start":129,"end":194,"location":{"line":9,"column":1},"kind":"InterfaceDeclaration","code":"export interface OrderLine {\n  sku: string;\n  quantity: number;\n}","symbol_ids":["975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b:129:194"]}],"gaps":[{"code":"module_side_effects","message":"Module initialization and side effects are not reconstructed or executed.","start":0,"end":2597,"path":"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts","source_hash":"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b"},{"code":"caller_coverage","message":"Callers and ambient project/library context are not exhaustively analysed.","start":1545,"end":2047,"path":"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts","source_hash":"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b"},{"code":"unresolved_reference","message":"No supported semantic declaration was found.","start":1652,"end":1655,"path":"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts","source_hash":"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b"},{"code":"unresolved_reference","message":"No supported semantic declaration was found.","start":1726,"end":1729,"path":"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts","source_hash":"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b"},{"code":"unresolved_reference","message":"No supported semantic declaration was found.","start":1730,"end":1734,"path":"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts","source_hash":"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b"},{"code":"unresolved_reference","message":"No supported semantic declaration was found.","start":1755,"end":1761,"path":"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts","source_hash":"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b"},{"code":"unresolved_reference","message":"No supported semantic declaration was found.","start":1762,"end":1771,"path":"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts","source_hash":"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b"},{"code":"unresolved_reference","message":"No supported semantic declaration was found.","start":1777,"end":1785,"path":"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts","source_hash":"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b"},{"code":"unresolved_reference","message":"No supported semantic declaration was found.","start":1795,"end":1803,"path":"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts","source_hash":"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b"},{"code":"unresolved_reference","message":"No supported semantic declaration was found.","start":1828,"end":1833,"path":"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts","source_hash":"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b"},{"code":"unresolved_reference","message":"No supported semantic declaration was found.","start":1913,"end":1916,"path":"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts","source_hash":"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b"},{"code":"unresolved_reference","message":"No supported semantic declaration was found.","start":1934,"end":1937,"path":"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts","source_hash":"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b"},{"code":"unresolved_reference","message":"No supported semantic declaration was found.","start":1956,"end":1964,"path":"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts","source_hash":"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b"},{"code":"unresolved_reference","message":"No supported semantic declaration was found.","start":1980,"end":1985,"path":"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts","source_hash":"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b"},{"code":"unresolved_reference","message":"No supported semantic declaration was found.","start":1986,"end":1990,"path":"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts","source_hash":"975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b"}],"collection":{"max_depth":2,"max_dependency_chars":12000,"dependency_chars":65},"project":{"repository_root":"/Users/I337254/workspace/sharon-workspace/laya-context-router","config_path":"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/tsconfig.json","config_hash":"87139864318ec174310f4adce1aa1c7e0493763a6832b3410974764b983f4f4d","config_sources":[{"path":"/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/tsconfig.json","source_hash":"87139864318ec174310f4adce1aa1c7e0493763a6832b3410974764b983f4f4d"}]}}
```


### Selected method code inside that context

This is one field of the payload above, not the entire additionalContext.

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


<details>
<summary>All context fields, formatted for reading</summary>

Display formatting only; the exact original string is shown above.

```json
{
  "schema_version": 1,
  "path": "/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts",
  "source_hash": "975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b",
  "diagnostics": [],
  "limitations": [
    "Runtime callable bodies are discovered recursively; destructuring-bound callable expressions remain unsupported.",
    "Locations and ranges use UTF-16 code units; comments before declarations are excluded.",
    "Bound expression signatures include their immediate binding header and transparent wrappers; raw code is only the callable expression.",
    "Type-only signatures are not runtime implementation candidates; computed names are source text, never evaluated.",
    "Project graph uses parsed Classic/Node10 resolution only; automatic libraries/types, ambient globals, separate referenced projects and callers remain partial.",
    "Only repository .ts source units are collected. Bodyless declarations are flagged; package implementations and .d.ts source units are omitted; project modules are never executed.",
    "Dependency graph loading is capped at64 unique source attempts,4,000,000 cumulative foreign pre-read bytes and1,000,000 admitted foreign UTF16 source units; selected source is governed by the subprocess deadline."
  ],
  "callable": {
    "id": "975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b:1545:2047",
    "name": "consolidateOrderLines",
    "signature": "export function consolidateOrderLines(lines: readonly OrderLine[]): OrderLine[]",
    "start": 1545,
    "end": 2047,
    "location": {
      "line": 46,
      "column": 1
    }
  },
  "code": "export function consolidateOrderLines(lines: readonly OrderLine[]): OrderLine[] {\n  const quantities = new Map<string, number>();\n  for (const line of lines) {\n    const sku = line.sku.trim();\n    if (!sku || !Number.isInteger(line.quantity) || line.quantity <= 0) {\n      throw new Error('Order lines require a SKU and positive whole quantity');\n    }\n    quantities.set(sku, (quantities.get(sku) ?? 0) + line.quantity);\n  }\n  return Array.from(quantities, ([sku, quantity]) => ({ sku, quantity }));\n}",
  "display_code": "46: export function consolidateOrderLines(lines: readonly OrderLine[]): OrderLine[] {\n47:   const quantities = new Map<string, number>();\n48:   for (const line of lines) {\n49:     const sku = line.sku.trim();\n50:     if (!sku || !Number.isInteger(line.quantity) || line.quantity <= 0) {\n51:       throw new Error('Order lines require a SKU and positive whole quantity');\n52:     }\n53:     quantities.set(sku, (quantities.get(sku) ?? 0) + line.quantity);\n54:   }\n55:   return Array.from(quantities, ([sku, quantity]) => ({ sku, quantity }));\n56: }",
  "coverage": "partial",
  "dependencies": [
    {
      "id": "975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b:129:194",
      "path": "/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts",
      "source_hash": "975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b",
      "start": 129,
      "end": 194,
      "location": {
        "line": 9,
        "column": 1
      },
      "kind": "InterfaceDeclaration",
      "code": "export interface OrderLine {\n  sku: string;\n  quantity: number;\n}",
      "symbol_ids": [
        "975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b:129:194"
      ]
    }
  ],
  "gaps": [
    {
      "code": "module_side_effects",
      "message": "Module initialization and side effects are not reconstructed or executed.",
      "start": 0,
      "end": 2597,
      "path": "/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts",
      "source_hash": "975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b"
    },
    {
      "code": "caller_coverage",
      "message": "Callers and ambient project/library context are not exhaustively analysed.",
      "start": 1545,
      "end": 2047,
      "path": "/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts",
      "source_hash": "975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b"
    },
    {
      "code": "unresolved_reference",
      "message": "No supported semantic declaration was found.",
      "start": 1652,
      "end": 1655,
      "path": "/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts",
      "source_hash": "975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b"
    },
    {
      "code": "unresolved_reference",
      "message": "No supported semantic declaration was found.",
      "start": 1726,
      "end": 1729,
      "path": "/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts",
      "source_hash": "975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b"
    },
    {
      "code": "unresolved_reference",
      "message": "No supported semantic declaration was found.",
      "start": 1730,
      "end": 1734,
      "path": "/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts",
      "source_hash": "975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b"
    },
    {
      "code": "unresolved_reference",
      "message": "No supported semantic declaration was found.",
      "start": 1755,
      "end": 1761,
      "path": "/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts",
      "source_hash": "975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b"
    },
    {
      "code": "unresolved_reference",
      "message": "No supported semantic declaration was found.",
      "start": 1762,
      "end": 1771,
      "path": "/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts",
      "source_hash": "975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b"
    },
    {
      "code": "unresolved_reference",
      "message": "No supported semantic declaration was found.",
      "start": 1777,
      "end": 1785,
      "path": "/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts",
      "source_hash": "975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b"
    },
    {
      "code": "unresolved_reference",
      "message": "No supported semantic declaration was found.",
      "start": 1795,
      "end": 1803,
      "path": "/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts",
      "source_hash": "975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b"
    },
    {
      "code": "unresolved_reference",
      "message": "No supported semantic declaration was found.",
      "start": 1828,
      "end": 1833,
      "path": "/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts",
      "source_hash": "975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b"
    },
    {
      "code": "unresolved_reference",
      "message": "No supported semantic declaration was found.",
      "start": 1913,
      "end": 1916,
      "path": "/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts",
      "source_hash": "975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b"
    },
    {
      "code": "unresolved_reference",
      "message": "No supported semantic declaration was found.",
      "start": 1934,
      "end": 1937,
      "path": "/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts",
      "source_hash": "975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b"
    },
    {
      "code": "unresolved_reference",
      "message": "No supported semantic declaration was found.",
      "start": 1956,
      "end": 1964,
      "path": "/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts",
      "source_hash": "975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b"
    },
    {
      "code": "unresolved_reference",
      "message": "No supported semantic declaration was found.",
      "start": 1980,
      "end": 1985,
      "path": "/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts",
      "source_hash": "975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b"
    },
    {
      "code": "unresolved_reference",
      "message": "No supported semantic declaration was found.",
      "start": 1986,
      "end": 1990,
      "path": "/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/src/fulfillment/inventory.ts",
      "source_hash": "975bbd1a016da31d361aad477edf3307913f08a4eaa85de188877405ecdf376b"
    }
  ],
  "collection": {
    "max_depth": 2,
    "max_dependency_chars": 12000,
    "dependency_chars": 65
  },
  "project": {
    "repository_root": "/Users/I337254/workspace/sharon-workspace/laya-context-router",
    "config_path": "/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/tsconfig.json",
    "config_hash": "87139864318ec174310f4adce1aa1c7e0493763a6832b3410974764b983f4f4d",
    "config_sources": [
      {
        "path": "/Users/I337254/workspace/sharon-workspace/laya-context-router/experiments/fixtures/connected_project/tsconfig.json",
        "source_hash": "87139864318ec174310f4adce1aa1c7e0493763a6832b3410974764b983f4f4d"
      }
    ]
  }
}
```

</details>


## Input from Claude (replayed)

```json
{
  "session_id": "synthetic-hook-inventory",
  "transcript_path": "unused.jsonl",
  "permission_mode": "default",
  "hook_event_name": "UserPromptSubmit",
  "cwd": "/Users/I337254/workspace/sharon-workspace/laya-context-router",
  "prompt": "Explain `experiments/fixtures/connected_project/src/fulfillment/inventory.ts`: how does consolidateOrderLines combine quantities for repeated SKUs? Focus on this one method."
}
```


## Laya request 1

Request prepared: yes. Agent ready: True. Response received: True. Validated: True.
Preparing a request alone does not prove inference ran.


## Requested model and temperature

```json
{
  "model": "aac6fef/laya-typed-decisions-mlx",
  "temperature": null,
  "lang": "en"
}
```


## Text submitted to Laya

```json
"Explain `experiments/fixtures/connected_project/src/fulfillment/inventory.ts`: how does consolidateOrderLines combine quantities for repeated SKUs? Focus on this one method."
```


## Exact questions and choices

```json
{
  "method": {
    "type": "choice",
    "instructions": "Select exactly one callable that the request asks to explain. Choose none_or_unclear when no single callable is appropriate.",
    "criteria": {
      "validateStockItem": "export function validateStockItem(item: StockItem): void",
      "findStockItem": "export function findStockItem(stock: readonly StockItem[], sku: string): StockItem",
      "availableQuantity": "export function availableQuantity(item: StockItem): number",
      "consolidateOrderLines": "export function consolidateOrderLines(lines: readonly OrderLine[]): OrderLine[]",
      "reserveOrderStock": "export function reserveOrderStock(stock: readonly StockItem[], lines: readonly OrderLine[]): StockItem[]",
      "none_or_unclear": "No single matching callable, or unclear request."
    }
  },
  "multiple_relevant": {
    "type": "noul",
    "instructions": "Does the request require explaining more than one candidate callable?"
  }
}
```


## Raw Laya response

```json
{
  "model": "laya-rl-agent",
  "answers": {
    "method": {
      "type": "choice",
      "choice": "consolidateOrderLines",
      "probabilities": {
        "validateStockItem": 0.0207,
        "findStockItem": 0.01,
        "availableQuantity": 0.0102,
        "consolidateOrderLines": 0.9215,
        "reserveOrderStock": 0.0097,
        "none_or_unclear": 0.0279
      },
      "confidence": 0.7805,
      "answer_confidence": 0.9215,
      "action": {
        "act_probability": 1.0
      }
    },
    "multiple_relevant": {
      "type": "noul",
      "noul": 0.288,
      "confidence": 0.712,
      "answer_confidence": 0.712,
      "action": {
        "act_probability": 1.0
      }
    }
  },
  "usage": {
    "input_tokens": 284,
    "output_tokens": 0,
    "state_tokens": 43,
    "state_tokens_dropped": 0,
    "truncated": false,
    "truncated_questions": []
  }
}
```


## Enriched answers (including gap)

```json
{
  "method": {
    "type": "choice",
    "choice": "consolidateOrderLines",
    "probabilities": {
      "validateStockItem": 0.0207,
      "findStockItem": 0.01,
      "availableQuantity": 0.0102,
      "consolidateOrderLines": 0.9215,
      "reserveOrderStock": 0.0097,
      "none_or_unclear": 0.0279
    },
    "confidence": 0.7805,
    "answer_confidence": 0.9215,
    "action": {
      "act_probability": 1.0
    },
    "probability_gap": 0.8936,
    "normalized_entropy": 0.2195
  },
  "multiple_relevant": {
    "type": "noul",
    "noul": 0.288,
    "confidence": 0.712,
    "answer_confidence": 0.712,
    "action": {
      "act_probability": 1.0
    },
    "distance_from_boundary": 0.212
  }
}
```


## Rules evaluated

```json
{
  "method": {
    "question": "method",
    "policy": "method-selection",
    "conditions": [
      {
        "field": "answer_confidence",
        "op": "gte",
        "value": 0.5
      },
      {
        "field": "probability_gap",
        "op": "gte",
        "value": 0.15
      }
    ]
  },
  "multiple_relevant": {
    "question": "multiple_relevant",
    "policy": "multiple-methods",
    "conditions": [
      {
        "field": "answer_confidence",
        "op": "gte",
        "value": 0.5
      }
    ]
  }
}
```


## Answers accepted or rejected

```json
{
  "method": {
    "answer": "consolidateOrderLines",
    "decided": true,
    "reason": null
  },
  "multiple_relevant": {
    "answer": "no",
    "decided": true,
    "reason": null
  }
}
```


## Errors observed

```json
[
  {
    "type": "ValueError",
    "message": "context_budget_exceeded",
    "traceback": "Traceback (most recent call last):\n  File \"/Users/I337254/workspace/sharon-workspace/laya-context-router/hooks/user_prompt_submit.py\", line 118, in main\n    raise ValueError('context_budget_exceeded')\nValueError: context_budget_exceeded\n"
  }
]
```


## Execution timeline


- 2026-10-30T19:49:42.934+02:00 — hook.invoked

- 2026-10-30T19:49:42.969+02:00 — flow.started

- 2026-10-30T19:49:42.971+02:00 — extractor.request_started

- 2026-10-30T19:49:43.081+02:00 — extractor.helper_returned

- 2026-10-30T19:49:43.085+02:00 — flow.references_detected

- 2026-10-30T19:49:43.087+02:00 — extractor.request_started

- 2026-10-30T19:49:43.179+02:00 — extractor.helper_returned

- 2026-10-30T19:49:43.182+02:00 — flow.file_resolved

- 2026-10-30T19:49:43.183+02:00 — extractor.request_started

- 2026-10-30T19:49:43.286+02:00 — extractor.helper_returned

- 2026-10-30T19:49:43.288+02:00 — extractor.outline_validated

- 2026-10-30T19:49:43.290+02:00 — questions.load_started

- 2026-10-30T19:49:43.296+02:00 — questions.loaded

- 2026-10-30T19:49:43.298+02:00 — questions.prepared

- 2026-10-30T19:49:43.300+02:00 — laya.prediction_started

- 2026-10-30T19:49:43.301+02:00 — laya.load_started

- 2026-10-30T19:49:44.643+02:00 — laya.load_completed

- 2026-10-30T19:49:44.737+02:00 — laya.response_received

- 2026-10-30T19:49:44.740+02:00 — laya.response_validated

- 2026-10-30T19:49:44.742+02:00 — enrichment.started

- 2026-10-30T19:49:44.744+02:00 — enrichment.completed

- 2026-10-30T19:49:44.746+02:00 — rules.evaluation_started

- 2026-10-30T19:49:44.748+02:00 — rules.decision

- 2026-10-30T19:49:44.750+02:00 — enrichment.started

- 2026-10-30T19:49:44.751+02:00 — enrichment.completed

- 2026-10-30T19:49:44.753+02:00 — rules.evaluation_started

- 2026-10-30T19:49:44.754+02:00 — rules.decision

- 2026-10-30T19:49:44.756+02:00 — flow.method_selected

- 2026-10-30T19:49:44.757+02:00 — extractor.request_started

- 2026-10-30T19:49:44.888+02:00 — extractor.helper_returned

- 2026-10-30T19:49:44.892+02:00 — extractor.context_validated

- 2026-10-30T19:49:44.894+02:00 — flow.finished

- 2026-10-30T19:49:44.897+02:00 — hook.response_prepared

- 2026-10-30T19:49:44.899+02:00 — hook.response_rejected

- 2026-10-30T19:49:44.901+02:00 — hook.failed


## Diagnostics from stderr (can include SDK progress)

```json
"\nFetching 6 files:   0%|          | 0/6 [00:00<?, ?it/s]\nFetching 6 files: 100%|██████████| 6/6 [00:00<00:00, 2452.09it/s]\n/opt/homebrew/lib/python3.11/site-packages/laya_mlx/agent.py:195: RuntimeWarning: laya: this checkpoint ships temperatures outside [0.5, 5] which would distort confidence; clamping choice:11+=0.10058280825614929 -> 0.5. Treat confidence from the affected buckets as uncalibrated.\n  ) = read_temperatures(self.cfg)\nlaya hook noop: ValueError: context_budget_exceeded\n"
```


## Replay error

```json
null
```


## Trace warnings

```json
[]
```


Source log: `/Users/I337254/workspace/sharon-workspace/laya-context-router/logs/debug.jsonl`. `trace.jsonl` contains this hook PID's captured log entries only; `details.json` contains the full report, including raw stdout.
