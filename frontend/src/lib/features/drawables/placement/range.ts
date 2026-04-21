// frontend/src/lib/drawables/placement/range.ts
import type { ChartPoint, PlacementMachine } from '../types';

export interface RangeGeo {
  startTime: number;
  startPrice: number;
  endTime: number;
  endPrice: number;
}

export function rangePlacement(): PlacementMachine<RangeGeo> {
  let state:
    | { phase: 'idle' }
    | { phase: 'drawing'; geo: RangeGeo }
    | { phase: 'done' } = { phase: 'idle' };
  let callback: ((geo: RangeGeo) => void) | null = null;

  return {
    onPointerDown(pt: ChartPoint) {
      if (state.phase !== 'idle') return;
      state = {
        phase: 'drawing',
        geo: {
          startTime: pt.time,
          startPrice: pt.price,
          endTime: pt.time,
          endPrice: pt.price,
        },
      };
    },
    onPointerMove(pt: ChartPoint) {
      if (state.phase !== 'drawing') return;
      state = {
        phase: 'drawing',
        geo: { ...state.geo, endTime: pt.time, endPrice: pt.price },
      };
    },
    onPointerUp(pt: ChartPoint) {
      if (state.phase !== 'drawing') return;
      const final: RangeGeo = {
        ...state.geo,
        endTime: pt.time,
        endPrice: pt.price,
      };
      state = { phase: 'done' };
      callback?.(final);
    },
    get preview() {
      return state.phase === 'drawing' ? { geometry: state.geo } : null;
    },
    onComplete(cb) {
      callback = cb;
    },
    cancel() {
      state = { phase: 'done' };
    },
    get done() {
      return state.phase === 'done';
    },
  };
}
