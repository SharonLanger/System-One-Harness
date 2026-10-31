import { consolidateOrderLines, findStockItem, OrderLine, StockItem } from './inventory';
import { PackingCalculator, Parcel } from './packing';

export interface ShippingRates {
  perParcel: number;
  perKilogram: number;
  insurancePercent: number;
}

export function merchandiseValue(stock: readonly StockItem[], lines: readonly OrderLine[]): number {
  const consolidated = consolidateOrderLines(lines);
  let value = 0;
  for (const line of consolidated) {
    const item = findStockItem(stock, line.sku);
    value += item.unitPrice * line.quantity;
  }
  return Math.round(value * 100) / 100;
}

export function validateShippingRates(rates: ShippingRates): void {
  const amounts = [rates.perParcel, rates.perKilogram, rates.insurancePercent];
  for (const amount of amounts) {
    if (!Number.isFinite(amount) || amount < 0) {
      throw new Error('Shipping rates must be finite and nonnegative');
    }
  }
  if (rates.insurancePercent > 100) throw new Error('Insurance percentage cannot exceed 100');
}

export function parcelShippingCharge(parcels: readonly Parcel[], rates: ShippingRates): number {
  validateShippingRates(rates);
  const billableKilograms = PackingCalculator.billableWeight(parcels);
  const handlingCharge = parcels.length * rates.perParcel;
  const weightCharge = billableKilograms * rates.perKilogram;
  const totalCharge = handlingCharge + weightCharge;
  return Math.round(totalCharge * 100) / 100;
}

export function insuranceCharge(value: number, rates: ShippingRates): number {
  validateShippingRates(rates);
  if (!Number.isFinite(value) || value < 0) throw new Error('Declared value must be nonnegative');
  const percentage = rates.insurancePercent / 100;
  const rawCharge = value * percentage;
  const roundedCharge = Math.round(rawCharge * 100) / 100;
  return roundedCharge;
}

export function quoteOrderShipping(stock: readonly StockItem[], lines: readonly OrderLine[], capacityKg: number, rates: ShippingRates): number {
  const parcels = PackingCalculator.buildParcels(stock, lines, capacityKg);
  const declaredValue = merchandiseValue(stock, lines);
  const freight = parcelShippingCharge(parcels, rates);
  const insurance = insuranceCharge(declaredValue, rates);
  const completeQuote = freight + insurance;
  return Math.round(completeQuote * 100) / 100;
}
