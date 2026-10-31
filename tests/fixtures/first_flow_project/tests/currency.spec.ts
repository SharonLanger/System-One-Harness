import { CurrencyFormatter } from '../src/utils/currency';

function assertEqual(actual: string, expected: string): void {
  if (actual !== expected) throw new Error(`Expected ${expected}, received ${actual}`);
}

assertEqual(CurrencyFormatter.formatInvoice(12.5, 'USD'), '$12.50');
