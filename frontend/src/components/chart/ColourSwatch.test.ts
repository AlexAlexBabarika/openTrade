import { describe, expect, it } from 'vitest';
import colourSwatchSource from './ColourSwatch.svelte?raw';
import dialogContentSource from '$lib/components/ui/dialog/dialog-content.svelte?raw';

function zIndex(source: string): number {
  const match = source.match(/z-\[(\d+)\]/);
  if (!match) throw new Error('Expected an explicit z-index class');
  return Number(match[1]);
}

describe('ColourSwatch', () => {
  it('layers its picker above dialogs that contain the swatch', () => {
    expect(zIndex(colourSwatchSource)).toBeGreaterThan(
      zIndex(dialogContentSource),
    );
  });
});
