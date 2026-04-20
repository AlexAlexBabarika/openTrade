// frontend/src/lib/drawables/types.ts
import type { Component } from 'svelte';

/** A pixel coordinate on the chart container. */
export interface ScreenPoint {
  x: number;
  y: number;
}

/** A chart-space coordinate (time in unix seconds, price in instrument units). */
export interface ChartPoint {
  time: number;
  price: number;
}

/**
 * Maps chart-space ↔ screen-space. Provided by the chart to Renderers and
 * placement machines. `version` bumps whenever pan/zoom/resize invalidates
 * cached coordinates, so consumers can depend on it in `$derived`.
 */
export interface CoordMap {
  version: number;
  plotWidth: number;
  timeToX: (t: number) => number | null;
  xToTime: (x: number) => number | null;
  priceToY: (p: number) => number | null;
  yToPrice: (y: number) => number | null;
}

/** A single drawable instance stored in the drawables store. */
export interface Drawable<Geo = unknown, Params = unknown, Style = unknown> {
  id: string;
  type: string;
  symbol: string;
  geometry: Geo;
  params: Params;
  style: Style;
  createdAt: number;
}

/** Popup action descriptor. Every tool gets settings + delete by default. */
export type PopupAction =
  | { id: 'settings'; label: string }
  | { id: 'delete'; label: string }
  | { id: 'custom'; label: string; handler: (drawable: Drawable) => void };

/** Context passed to `createPlacement`. Provides the chart mappers the machine needs. */
export interface PlacementCtx {
  coordMap: CoordMap;
  symbol: string;
}

/**
 * State machine that turns raw pointer events into a completed geometry.
 * Tools return an instance from `createPlacement(ctx)`.
 */
export interface PlacementMachine<Geo> {
  onPointerDown(pt: ChartPoint): void;
  onPointerMove(pt: ChartPoint): void;
  onPointerUp(pt: ChartPoint): void;
  /** Preview geometry while placing (for live rendering). Null before first event. */
  readonly preview: { geometry: Geo } | null;
  /** Called once when placement is final. */
  onComplete(cb: (geometry: Geo) => void): void;
  /** Called if placement is cancelled (e.g. Escape). */
  cancel(): void;
  /** True after onComplete or cancel was called. Machine should not be used further. */
  readonly done: boolean;
}

export interface ComputeCtx {
  candles: readonly import('../types').OHLCVCandle[];
  provider: string;
  symbol: string;
  interval: string;
  signal: AbortSignal;
}

/** The contract every registered tool must satisfy. */
export interface DrawableTool<
  Geo = unknown,
  Params = unknown,
  Style = unknown,
  Data = void,
> {
  type: string;
  label: string;
  icon: Component;
  defaults: { params: Params; style: Style };

  schemaVersion: number;
  migrate?: (raw: unknown) => Drawable<Geo, Params, Style> | null;

  createPlacement(ctx: PlacementCtx): PlacementMachine<Geo>;
  compute?: (
    drawable: Drawable<Geo, Params, Style>,
    ctx: ComputeCtx,
  ) => Data | Promise<Data>;

  Renderer: Component<RendererProps<Geo, Params, Style, Data>>;
  Settings: Component<SettingsProps<Geo, Params, Style>>;
  popupActions?: PopupAction[];
}

/** Renderer prop shape — enforced by `DrawableTool.Renderer` typing above. */
export interface RendererProps<Geo, Params, Style, Data> {
  drawable: Drawable<Geo, Params, Style>;
  data: Data | undefined;
  selected: boolean;
  coordMap: CoordMap;
  onGeometryChange: (geo: Geo) => void;
  onRequestSelect: () => void;
  onAnchorPoint: (pt: ScreenPoint | null) => void;
}

/**
 * Settings prop shape — enforced by `DrawableTool.Settings` typing above.
 * The modal owns staged copies of `params` and `style`; the component mutates
 * their properties in place via `bind:`. No live-apply — the modal commits
 * on Ok.
 */
export interface SettingsProps<_Geo, Params, Style> {
  params: Params;
  style: Style;
}
