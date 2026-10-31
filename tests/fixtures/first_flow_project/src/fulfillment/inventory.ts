export interface StockItem {
  sku: string;
  available: number;
  reserved: number;
  weightKg: number;
  unitPrice: number;
}

export interface OrderLine {
  sku: string;
  quantity: number;
}

export function validateStockItem(item: StockItem): void {
  if (!item.sku.trim()) throw new Error('Stock SKU is required');
  const values = [item.available, item.reserved, item.weightKg, item.unitPrice];
  if (values.some(value => !Number.isFinite(value) || value < 0)) {
    throw new Error('Stock values must be finite and nonnegative');
  }
  if (!Number.isInteger(item.available) || !Number.isInteger(item.reserved)) {
    throw new Error('Stock quantities must be whole numbers');
  }
  if (item.reserved > item.available) throw new Error('Reservations exceed stock');
}

export function findStockItem(stock: readonly StockItem[], sku: string): StockItem {
  const normalizedSku = sku.trim();
  if (!normalizedSku) throw new Error('Order SKU is required');
  const matches = stock.filter(item => item.sku === normalizedSku);
  if (matches.length !== 1) {
    throw new Error(`Expected one stock record for ${normalizedSku}`);
  }
  validateStockItem(matches[0]);
  return matches[0];
}

export function availableQuantity(item: StockItem): number {
  validateStockItem(item);
  const physicalQuantity = item.available;
  const committedQuantity = item.reserved;
  const remainingQuantity = physicalQuantity - committedQuantity;
  if (remainingQuantity < 0) throw new Error('Available stock cannot be negative');
  return remainingQuantity;
}

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

export function reserveOrderStock(stock: readonly StockItem[], lines: readonly OrderLine[]): StockItem[] {
  const consolidated = consolidateOrderLines(lines);
  const requested = new Map<string, number>();
  for (const line of consolidated) {
    const item = findStockItem(stock, line.sku);
    if (availableQuantity(item) < line.quantity) throw new Error(`Insufficient stock for ${line.sku}`);
    requested.set(line.sku, line.quantity);
  }
  return stock.map(item => ({ ...item, reserved: item.reserved + (requested.get(item.sku) ?? 0) }));
}
