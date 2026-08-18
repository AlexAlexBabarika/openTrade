/**
 * Optional drawable/chart profiling for Chrome DevTools **Performance** → **Timings** / **User Timing**.
 * Set `localStorage.openquant:profileDrawables = '1'` then look for `openquant:drawables:workKey` and
 * `openquant:drawables:compute-pass` when tuning ChartDrawablesCompute / store paths.
 */

let measureSeq = 0;

export function isDrawablesProfilingEnabled(): boolean {
  return (
    import.meta.env.DEV &&
    typeof performance !== 'undefined' &&
    typeof performance.mark === 'function' &&
    typeof localStorage !== 'undefined' &&
    localStorage.getItem('openquant:profileDrawables') === '1'
  );
}

/** Wrap synchronous work; shows up as a User Timing measure when profiling is enabled. */
export function measureDrawablesSync<T>(measureName: string, fn: () => T): T {
  if (!isDrawablesProfilingEnabled()) return fn();
  const id = ++measureSeq;
  const start = `openquant:${measureName}:s:${id}`;
  const end = `openquant:${measureName}:e:${id}`;
  const label = `openquant:${measureName}`;
  performance.mark(start);
  try {
    return fn();
  } finally {
    performance.mark(end);
    try {
      performance.measure(label, start, end);
    } catch {
      /* ignore duplicate / missing mark edge cases */
    }
  }
}
