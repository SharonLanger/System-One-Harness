import { TAX_RATE } from './constants';
import { roundToCents } from '../utils/rounding';
import { calculateAdjustment } from './adjustments';
import { Invoice } from '../types/invoice';

export function calculateInvoiceTotal(invoice: Invoice): number {
  if (!invoice.id.trim()) throw new Error('Invoice id is required');
  if (invoice.discount < 0) throw new Error('Discount cannot be negative');
  const subtotal = invoice.lines.reduce((sum, line) => sum + line.unitPrice * line.quantity, 0);
  if (invoice.lines.some(line => line.quantity < 0 || line.unitPrice < 0)) {
    throw new Error('Invoice lines cannot have negative prices or quantities');
  }
  const boundedDiscount = Math.min(invoice.discount, subtotal);
  const taxAmount = subtotal * TAX_RATE;
  const taxable = subtotal + taxAmount;
  const adjustment = calculateAdjustment(boundedDiscount);
  const beforeRounding = taxable - boundedDiscount + adjustment;
  return roundToCents(beforeRounding);
}

export function calculateInvoiceTotalWithAdjustment(invoice: Invoice, adjustment: number): number {
  const base = calculateInvoiceTotal(invoice);
  return roundToCents(base + adjustment);
}
