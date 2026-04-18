// frontend/src/lib/drawables/tools/ruler/tool.ts
import RulerIcon from '@lucide/svelte/icons/ruler';
import type { DrawableTool, Drawable, ComputeCtx } from '../../types';
import { rangePlacement, type RangeGeo } from '../../placement/range';
import { computeStats, type RulerStats } from './compute';
import Renderer from './Renderer.svelte';
import Settings from './Settings.svelte';

export const RULER_TYPE = 'ruler' as const;

export type RulerGeo = RangeGeo;
export interface RulerParams {
  [k: string]: never;
}
export interface RulerStyle {
  upColor: string;
  downColor: string;
  showStats: boolean;
}
export type RulerDrawable = Drawable<RulerGeo, RulerParams, RulerStyle>;

const defaultStyle: RulerStyle = {
  upColor: 'rgb(38, 166, 154)',
  downColor: 'rgb(239, 83, 80)',
  showStats: true,
};

export const rulerTool: DrawableTool<
  RulerGeo,
  RulerParams,
  RulerStyle,
  RulerStats
> = {
  type: RULER_TYPE,
  label: 'Ruler',
  icon: RulerIcon,
  defaults: { params: {}, style: defaultStyle },
  schemaVersion: 1,

  createPlacement: () => rangePlacement(),

  compute: (d: RulerDrawable, ctx: ComputeCtx) =>
    computeStats(d.geometry, ctx.candles),

  Renderer,
  Settings,
};
