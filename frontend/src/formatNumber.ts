// Keep small nonzero measurements visible instead of displaying a verified zero.
export function formatNumber(value: number): string {
  if (!Number.isFinite(value)) return 'Unavailable';
  if (value !== 0 && Math.abs(value) < .001) return value.toExponential(5);
  return value.toLocaleString(undefined, {maximumFractionDigits: 6});
}
