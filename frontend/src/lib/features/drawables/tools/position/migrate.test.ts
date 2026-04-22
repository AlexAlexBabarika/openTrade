import { describe, it, expect, beforeEach } from 'vitest';
import { positionLongTool } from './tool';
import { _resetRegistry } from '../../registry';
import { registerTool } from '../../registry';

describe('position tool migrate v1 geometry', () => {
  beforeEach(() => {
    _resetRegistry();
    registerTool(positionLongTool);
  });

  it('maps three timestamps to start/end span', () => {
    const raw = {
      id: 'a',
      type: 'position-long',
      symbol: 'AAPL',
      createdAt: 0,
      geometry: {
        entryTime: 100,
        stopTime: 50,
        targetTime: 200,
        entryPrice: 10,
        stopPrice: 9,
        targetPrice: 11,
      },
      params: {},
      style: positionLongTool.defaults.style,
      schemaVersion: 1,
    };
    const migrated = positionLongTool.migrate!(raw);
    expect(migrated).not.toBeNull();
    expect(migrated!.geometry).toEqual({
      startTime: 50,
      endTime: 200,
      entryPrice: 10,
      stopPrice: 9,
      targetPrice: 11,
    });
  });
});
