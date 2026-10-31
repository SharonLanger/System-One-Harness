import { consolidateOrderLines, findStockItem, OrderLine, StockItem } from './inventory';

export interface Parcel {
  index: number;
  weightKg: number;
  units: number;
}

export class PackingCalculator {
  static countUnits(lines: readonly OrderLine[]): number {
    const consolidated = consolidateOrderLines(lines);
    let totalUnits = 0;
    for (const line of consolidated) {
      totalUnits += line.quantity;
    }
    return totalUnits;
  }

  static totalWeight(stock: readonly StockItem[], lines: readonly OrderLine[]): number {
    const consolidated = consolidateOrderLines(lines);
    let totalWeightKg = 0;
    for (const line of consolidated) {
      const item = findStockItem(stock, line.sku);
      totalWeightKg += item.weightKg * line.quantity;
    }
    return Math.round(totalWeightKg * 1000) / 1000;
  }

  static buildParcels(stock: readonly StockItem[], lines: readonly OrderLine[], capacityKg: number): Parcel[] {
    if (!Number.isFinite(capacityKg) || capacityKg <= 0) throw new Error('Parcel capacity must be positive');
    const parcels: Parcel[] = [];
    for (const line of consolidateOrderLines(lines)) {
      const item = findStockItem(stock, line.sku);
      if (item.weightKg > capacityKg) throw new Error(`Item ${line.sku} exceeds parcel capacity`);
      for (let unit = 0; unit < line.quantity; unit += 1) {
        let parcel = parcels[parcels.length - 1];
        if (!parcel || parcel.weightKg + item.weightKg > capacityKg) {
          parcel = { index: parcels.length + 1, weightKg: 0, units: 0 };
          parcels.push(parcel);
        }
        parcel.weightKg += item.weightKg;
        parcel.units += 1;
      }
    }
    return parcels;
  }

  static billableWeight(parcels: readonly Parcel[]): number {
    let billedKilograms = 0;
    for (const parcel of parcels) {
      if (!Number.isFinite(parcel.weightKg) || parcel.weightKg < 0) throw new Error('Invalid parcel weight');
      const roundedWeight = Math.ceil(parcel.weightKg);
      billedKilograms += Math.max(1, roundedWeight);
    }
    return billedKilograms;
  }

  static packingSummary(stock: readonly StockItem[], lines: readonly OrderLine[], capacityKg: number): string {
    const units = PackingCalculator.countUnits(lines);
    const weight = PackingCalculator.totalWeight(stock, lines);
    const parcels = PackingCalculator.buildParcels(stock, lines, capacityKg);
    const billedWeight = PackingCalculator.billableWeight(parcels);
    const parcelLabel = parcels.length === 1 ? 'parcel' : 'parcels';
    return `${units} units, ${weight.toFixed(3)} kg, ${parcels.length} ${parcelLabel}, ${billedWeight} billable kg`;
  }
}
