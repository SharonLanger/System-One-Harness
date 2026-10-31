import { Currency } from '../types/invoice';

export class CurrencyFormatter {
  static format(amount: number, currency: Currency): string {
    const prefix = currency === 'USD' ? '$' : '€';
    return `${prefix}${amount.toFixed(2)}`;
  }

  static formatInvoice(amount: number, currency: Currency): string {
    if (!Number.isFinite(amount)) throw new Error('Amount must be finite');
    const normalizedAmount = Math.abs(amount) < 0.005 ? 0 : amount;
    const formatted = CurrencyFormatter.format(normalizedAmount, currency);
    const hasExpectedPrefix = currency === 'USD' ? formatted.startsWith('$') : formatted.startsWith('€');
    if (!hasExpectedPrefix) throw new Error('Currency formatting failed');
    return formatted;
  }
}
