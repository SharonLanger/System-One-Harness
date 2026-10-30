export interface Invoice {
  id: string;
  amount: number;
}

export function calculateTotal(items: Invoice[]): number {
  return items.reduce((total, item) => total + item.amount, 0);
}

export function formatInvoice(invoice: Invoice): string {
  return `${invoice.id}: ${invoice.amount}`;
}
