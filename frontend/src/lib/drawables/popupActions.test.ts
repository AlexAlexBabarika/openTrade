import { describe, it, expect } from 'vitest';
import { resolvePopupActions, DEFAULT_POPUP_ACTIONS } from './popupActions';
import type { DrawableTool } from './types';

function fakeTool(overrides: Partial<DrawableTool> = {}): DrawableTool {
  return {
    type: 't',
    label: 'T',
    icon: (() => null) as unknown as DrawableTool['icon'],
    defaults: { params: {}, style: {} },
    schemaVersion: 1,
    createPlacement: () => {
      throw new Error('not used');
    },
    Renderer: (() => null) as unknown as DrawableTool['Renderer'],
    Settings: (() => null) as unknown as DrawableTool['Settings'],
    ...overrides,
  };
}

describe('resolvePopupActions', () => {
  it('returns the defaults when tool.popupActions is undefined', () => {
    const tool = fakeTool();
    expect(resolvePopupActions(tool)).toEqual(DEFAULT_POPUP_ACTIONS);
  });

  it('returns tool.popupActions when provided', () => {
    const custom = [{ id: 'delete', label: 'Remove' } as const];
    const tool = fakeTool({ popupActions: custom });
    expect(resolvePopupActions(tool)).toBe(custom);
  });

  it('DEFAULT_POPUP_ACTIONS contains settings then delete in that order', () => {
    expect(DEFAULT_POPUP_ACTIONS.map(a => a.id)).toEqual([
      'settings',
      'delete',
    ]);
  });
});
