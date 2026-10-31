import { consolidateOrderLines, findStockItem, availableQuantity, OrderLine, reserveOrderStock, StockItem } from './inventory';
import { PackingCalculator, Parcel } from './packing';
import { quoteOrderShipping, ShippingRates } from './pricing';

export interface ShipmentOperations {
  checkAvailability(lines: readonly OrderLine[]): string[];
  reserve(lines: readonly OrderLine[]): StockItem[];
  planParcels(lines: readonly OrderLine[]): Parcel[];
  quote(lines: readonly OrderLine[]): number;
  describe(lines: readonly OrderLine[]): string;
}

export class ShipmentService implements ShipmentOperations {
  constructor(
    private readonly stock: readonly StockItem[],
    private readonly capacityKg: number,
    private readonly rates: ShippingRates,
  ) {}

  checkAvailability(lines: readonly OrderLine[]): string[] {
    const shortages: string[] = [];
    for (const line of consolidateOrderLines(lines)) {
      const item = findStockItem(this.stock, line.sku);
      const missingUnits = line.quantity - availableQuantity(item);
      if (missingUnits > 0) shortages.push(`${line.sku}: ${missingUnits} units short`);
    }
    return shortages;
  }

  reserve(lines: readonly OrderLine[]): StockItem[] {
    const shortages = this.checkAvailability(lines);
    if (shortages.length > 0) {
      throw new Error(shortages.join('; '));
    }
    const updatedStock = reserveOrderStock(this.stock, lines);
    return updatedStock;
  }

  planParcels(lines: readonly OrderLine[]): Parcel[] {
    const normalizedLines = consolidateOrderLines(lines);
    const parcels = PackingCalculator.buildParcels(this.stock, normalizedLines, this.capacityKg);
    const plannedUnits = parcels.reduce((sum, parcel) => sum + parcel.units, 0);
    const requestedUnits = PackingCalculator.countUnits(normalizedLines);
    if (plannedUnits !== requestedUnits) throw new Error('Parcel plan is incomplete');
    return parcels;
  }

  quote(lines: readonly OrderLine[]): number {
    const normalizedLines = consolidateOrderLines(lines);
    const parcels = this.planParcels(normalizedLines);
    if (parcels.length === 0) return 0;
    const shippingQuote = quoteOrderShipping(this.stock, normalizedLines, this.capacityKg, this.rates);
    if (!Number.isFinite(shippingQuote)) throw new Error('Shipping quote is invalid');
    return shippingQuote;
  }

  describe(lines: readonly OrderLine[]): string {
    const shortages = this.checkAvailability(lines);
    const availability = shortages.length === 0 ? 'ready' : shortages.join('; ');
    const packing = PackingCalculator.packingSummary(this.stock, lines, this.capacityKg);
    const quote = this.quote(lines);
    const priceLabel = quote.toFixed(2);
    return `${availability} | ${packing} | shipping ${priceLabel}`;
  }
}
