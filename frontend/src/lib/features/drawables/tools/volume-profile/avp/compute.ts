import type { Drawable, ComputeCtx } from '../../../types';
import { fetchVolumeProfile } from '../shared/api';
import type { VolumeProfileResponse } from '../shared/types';

export interface AvpGeo {
  time: number;
}
export interface AvpParams {
  rowSize: number;
  vaPercent: number;
}
export interface AvpStyle {
  showProfile: boolean;
  widthPct: number;
  placement: 'left' | 'right';
  upColor: string;
  downColor: string;
  showPOC: boolean;
  pocColor: string;
  showVAH: boolean;
  vahColor: string;
  showVAL: boolean;
  valColor: string;
}

export async function computeAvp(
  d: Drawable<AvpGeo, AvpParams, AvpStyle>,
  ctx: ComputeCtx,
): Promise<VolumeProfileResponse> {
  return fetchVolumeProfile(
    {
      provider: ctx.provider,
      symbol: ctx.symbol,
      startTs: d.geometry.time,
      rowSize: d.params.rowSize,
      vaPercent: d.params.vaPercent,
      interval: ctx.interval,
    },
    ctx.signal,
  );
}
