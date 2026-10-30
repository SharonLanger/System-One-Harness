import { OrderLine } from './inventory';
import { ShipmentOperations } from './shipment-service';

export interface ShippingRequest {
  orderId: string;
  lines: readonly OrderLine[];
}

export interface ShippingReportRow {
  orderId: string;
  ready: boolean;
  parcelCount: number;
  shippingCharge: number;
  summary: string;
}

export function buildShippingReportRow(service: ShipmentOperations, request: ShippingRequest): ShippingReportRow {
  const orderId = request.orderId.trim();
  if (!orderId) throw new Error('Order identifier is required');
  const shortages = service.checkAvailability(request.lines);
  const parcels = service.planParcels(request.lines);
  const shippingCharge = service.quote(request.lines);
  const summary = service.describe(request.lines);
  return { orderId, ready: shortages.length === 0, parcelCount: parcels.length, shippingCharge, summary };
}

export function buildShippingReport(service: ShipmentOperations, requests: readonly ShippingRequest[]): ShippingReportRow[] {
  const seenIds = new Set<string>();
  const rows: ShippingReportRow[] = [];
  for (const request of requests) {
    const row = buildShippingReportRow(service, request);
    if (seenIds.has(row.orderId)) throw new Error(`Duplicate order ${row.orderId}`);
    seenIds.add(row.orderId);
    rows.push(row);
  }
  return rows;
}

export function totalShippingCharges(rows: readonly ShippingReportRow[]): number {
  let total = 0;
  for (const row of rows) {
    if (!Number.isFinite(row.shippingCharge) || row.shippingCharge < 0) throw new Error('Invalid report charge');
    total += row.shippingCharge;
  }
  return Math.round(total * 100) / 100;
}

export function summarizeShippingReport(rows: readonly ShippingReportRow[]): string {
  const readyOrders = rows.filter(row => row.ready).length;
  const blockedOrders = rows.length - readyOrders;
  const parcelCount = rows.reduce((sum, row) => sum + row.parcelCount, 0);
  const totalCharge = totalShippingCharges(rows);
  const amountLabel = totalCharge.toFixed(2);
  return `${readyOrders} ready, ${blockedOrders} blocked, ${parcelCount} parcels, shipping ${amountLabel}`;
}

export function renderShippingManifest(rows: readonly ShippingReportRow[]): string {
  const orderedRows = [...rows].sort((left, right) => left.orderId < right.orderId ? -1 : left.orderId > right.orderId ? 1 : 0);
  const lines = ['Shipping manifest'];
  for (const row of orderedRows) {
    lines.push(`${row.orderId}: ${row.summary}`);
  }
  lines.push(summarizeShippingReport(orderedRows));
  return lines.join('\n');
}
