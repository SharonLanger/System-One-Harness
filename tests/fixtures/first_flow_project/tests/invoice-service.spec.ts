import { calculateInvoiceTotal } from '../src/billing/invoice-service';
import { Invoice } from '../src/types/invoice';

function assertEqual(actual: number, expected: number): void {
  if (actual !== expected) throw new Error(`Expected ${expected}, received ${actual}`);
}

const sample: Invoice = {
  id: 'INV-42',
  lines: [{ sku: 'BOOK', unitPrice: 10, quantity: 2 }],
  discount: 1
};

assertEqual(calculateInvoiceTotal(sample), 22.6);
