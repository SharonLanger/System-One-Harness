export interface InvoiceLine {
  sku: string;
  unitPrice: number;
  quantity: number;
}

export interface Invoice {
  id: string;
  lines: InvoiceLine[];
  discount: number;
}

export type Currency = 'USD' | 'EUR';
