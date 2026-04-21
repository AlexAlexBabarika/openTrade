import { CrosshairMode } from 'lightweight-charts';
import Move from '@lucide/svelte/icons/move';
import Magnet from '@lucide/svelte/icons/magnet';
import CandlestickChart from '@lucide/svelte/icons/candlestick-chart';
import EyeOff from '@lucide/svelte/icons/eye-off';
import type { Component } from 'svelte';

export type CrosshairModeName = 'normal' | 'magnet' | 'magnetOHLC' | 'hidden';

export const CROSSHAIR_MODES: {
  value: CrosshairModeName;
  label: string;
  icon: Component;
}[] = [
  { value: 'normal', label: 'Normal', icon: Move },
  { value: 'magnet', label: 'Magnet', icon: Magnet },
  { value: 'magnetOHLC', label: 'Magnet OHLC', icon: CandlestickChart },
  { value: 'hidden', label: 'Hidden', icon: EyeOff },
];

export function toCrosshairMode(name: CrosshairModeName): CrosshairMode {
  switch (name) {
    case 'normal':
      return CrosshairMode.Normal;
    case 'magnet':
      return CrosshairMode.Magnet;
    case 'magnetOHLC':
      return CrosshairMode.MagnetOHLC;
    case 'hidden':
      return CrosshairMode.Hidden;
  }
}
