// Tiny RAF-driven damped harmonic spring. Used to animate the toolbox panel
// drawer with a perceptible bounce after a drag release or click toggle.

export interface SpringOptions {
  from: number;
  to: number;
  velocity?: number;
  stiffness?: number;
  damping?: number;
  mass?: number;
  // Considered settled when |x - to| and |v| are both under these.
  precision?: number;
  velocityPrecision?: number;
  onUpdate: (value: number) => void;
  onDone?: () => void;
}

const DEFAULTS = {
  stiffness: 180,
  damping: 18,
  mass: 1,
  precision: 0.001,
  velocityPrecision: 0.05,
};

// Step a damped harmonic oscillator forward by dt seconds using semi-implicit
// Euler. Sub-stepping keeps it stable for stiff springs / large frame gaps.
export function stepSpring(
  x: number,
  v: number,
  target: number,
  dt: number,
  stiffness = DEFAULTS.stiffness,
  damping = DEFAULTS.damping,
  mass = DEFAULTS.mass,
): { x: number; v: number } {
  const maxStep = 1 / 240;
  let remaining = dt;
  let cx = x;
  let cv = v;
  while (remaining > 0) {
    const h = Math.min(maxStep, remaining);
    const a = (-stiffness * (cx - target) - damping * cv) / mass;
    cv += a * h;
    cx += cv * h;
    remaining -= h;
  }
  return { x: cx, v: cv };
}

export function runSpring(opts: SpringOptions): () => void {
  const stiffness = opts.stiffness ?? DEFAULTS.stiffness;
  const damping = opts.damping ?? DEFAULTS.damping;
  const mass = opts.mass ?? DEFAULTS.mass;
  const precision = opts.precision ?? DEFAULTS.precision;
  const velocityPrecision =
    opts.velocityPrecision ?? DEFAULTS.velocityPrecision;

  let x = opts.from;
  let v = opts.velocity ?? 0;
  let last = performance.now();
  let cancelled = false;
  let raf = 0;

  const tick = (now: number) => {
    if (cancelled) return;
    const dt = Math.min(0.064, (now - last) / 1000);
    last = now;
    const next = stepSpring(x, v, opts.to, dt, stiffness, damping, mass);
    x = next.x;
    v = next.v;
    opts.onUpdate(x);
    if (Math.abs(x - opts.to) < precision && Math.abs(v) < velocityPrecision) {
      opts.onUpdate(opts.to);
      opts.onDone?.();
      return;
    }
    raf = requestAnimationFrame(tick);
  };

  raf = requestAnimationFrame(tick);
  return () => {
    cancelled = true;
    cancelAnimationFrame(raf);
  };
}
