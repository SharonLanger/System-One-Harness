import { calculateInvoiceTotal, calculateInvoiceTotalWithAdjustment } from './invoice-service';
import { calculateAdjustment } from './adjustments';
import { Invoice } from '../types/invoice';

export class InvoiceController {
  public getTotal(invoice: Invoice): number {
    return calculateInvoiceTotal(invoice);
  }

  public getAdjustedTotal(invoice: Invoice, rawAdjustment: number): number {
    const adjustment = calculateAdjustment(rawAdjustment);
    return calculateInvoiceTotalWithAdjustment(invoice, adjustment);
  }
}
