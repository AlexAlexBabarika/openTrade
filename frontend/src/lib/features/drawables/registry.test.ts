// frontend/src/lib/drawables/registry.test.ts
import { describe, it, expect, beforeEach } from 'vitest';
import {
  registerTool,
  getTool,
  getRegisteredBundledTool,
  listTools,
  _resetRegistry,
} from './registry';
import type { DrawableTool } from './types';
import { rulerTool } from './tools/ruler/tool';

function fakeTool(type: string): DrawableTool {
  return {
    type,
    label: type,
    icon: (() => null) as unknown as DrawableTool['icon'],
    defaults: { params: {}, style: {} },
    schemaVersion: 1,
    createPlacement: () => {
      throw new Error('not used');
    },
    Renderer: (() => null) as unknown as DrawableTool['Renderer'],
    Settings: (() => null) as unknown as DrawableTool['Settings'],
  };
}

describe('registry', () => {
  beforeEach(() => _resetRegistry());

  it('registers a tool and retrieves it by type', () => {
    const t = fakeTool('custom-tool');
    registerTool(t);
    expect(getTool('custom-tool')).toBe(t);
  });

  it('returns undefined for unknown type', () => {
    expect(getTool('nope')).toBeUndefined();
  });

  it('getRegisteredBundledTool returns the catalog-shaped tool from the registry', () => {
    _resetRegistry();
    registerTool(rulerTool);
    const t = getRegisteredBundledTool('ruler');
    expect(t).toBe(rulerTool);
    expect(t?.type).toBe('ruler');
  });

  it('lists tools in registration order', () => {
    registerTool(fakeTool('a'));
    registerTool(fakeTool('b'));
    registerTool(fakeTool('c'));
    expect(listTools().map(t => t.type)).toEqual(['a', 'b', 'c']);
  });

  it('throws when registering a duplicate type', () => {
    registerTool(fakeTool('dup'));
    expect(() => registerTool(fakeTool('dup'))).toThrow(/already registered/);
  });
});
