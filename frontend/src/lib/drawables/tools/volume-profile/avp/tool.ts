import TrendingUp from '@lucide/svelte/icons/trending-up';
import type {
  Drawable,
  DrawableTool,
  PlacementMachine,
  ChartPoint,
} from '../../../types';
import { pointPlacement } from '../../../placement/point';
import type { VolumeProfileResponse } from '../shared/types';
import type { AvpGeo, AvpParams, AvpStyle } from './compute';
import { computeAvp } from './compute';
import Renderer from './Renderer.svelte';
import Settings from './Settings.svelte';

export type { AvpGeo, AvpParams, AvpStyle };
export type AvpDrawable = Drawable<AvpGeo, AvpParams, AvpStyle>;

function avpPlacement(): PlacementMachine<AvpGeo> {
  const inner = pointPlacement();
  let cb: ((geo: AvpGeo) => void) | null = null;
  inner.onComplete(geo => cb?.({ time: geo.time }));
  return {
    onPointerDown: (p: ChartPoint) => inner.onPointerDown(p),
    onPointerMove: (p: ChartPoint) => inner.onPointerMove(p),
    onPointerUp: (p: ChartPoint) => inner.onPointerUp(p),
    get preview() {
      return null;
    },
    onComplete(fn) {
      cb = fn;
    },
    cancel: () => inner.cancel(),
    get done() {
      return inner.done;
    },
  };
}

export const avpTool: DrawableTool<
  AvpGeo,
  AvpParams,
  AvpStyle,
  VolumeProfileResponse
> = {
  type: 'avp',
  label: 'Anchored Volume Profile',
  icon: TrendingUp,
  schemaVersion: 1,
  defaults: {
    params: { rowSize: 1, vaPercent: 0.7 },
    style: {
      showProfile: true,
      widthPct: 25,
      placement: 'right',
      upColor: '#26a69a',
      downColor: '#ef5350',
      showPOC: true,
      pocColor: '#ffeb3b',
      showVAH: true,
      vahColor: '#2196f3',
      showVAL: true,
      valColor: '#2196f3',
    },
  },
  createPlacement: () => avpPlacement(),
  compute: computeAvp,
  Renderer,
  Settings,
};
