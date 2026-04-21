// frontend/src/lib/drawables/placement/point.ts
import type { ChartPoint, PlacementMachine } from '../types';

export interface PointGeo {
  time: number;
  price: number;
}

export function pointPlacement(): PlacementMachine<PointGeo> {
  let callback: ((geo: PointGeo) => void) | null = null;
  let done = false;

  return {
    onPointerDown(pt: ChartPoint) {
      if (done) return;
      done = true;
      callback?.({ time: pt.time, price: pt.price });
    },
    onPointerMove() {
      /* point placement completes on pointerDown; moves are ignored */
    },
    onPointerUp() {
      /* see onPointerMove */
    },
    get preview() {
      return null;
    },
    onComplete(cb) {
      callback = cb;
    },
    cancel() {
      done = true;
    },
    get done() {
      return done;
    },
  };
}
