/** Real measured fetch time. A cold /api/home/highlights call genuinely
 * takes several seconds (it scans 8 competitions) — shown in seconds
 * above 1000ms so it reads clearly instead of as an alarming "ms" value,
 * without hiding or rounding away the real number. */
export function formatLatency(ms: number): string {
  if (ms >= 1000) {
    return `${(ms / 1000).toFixed(1)} s`;
  }
  return `${ms} ms`;
}
