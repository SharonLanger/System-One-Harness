import { addOne, double, subtract } from '../math/arithmetic';
import { MAX_DISCOUNT } from './constants';

export function calculateAdjustment(raw: number): number {
  const bumped = addOne(raw);
  const scaled = double(bumped);
  return subtract(scaled, MAX_DISCOUNT);
}
