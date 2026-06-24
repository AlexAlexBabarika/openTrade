import { describe, it, expect } from 'vitest';
import { truncateRunId, formatDelta } from './format';

describe('truncateRunId', () => {
  it('shows first 8 chars with an ellipsis', () => {
    expect(truncateRunId('a'.repeat(64))).toBe('aaaaaaaa…');
  });
  it('returns short ids unchanged', () => {
    expect(truncateRunId('abc')).toBe('abc');
  });
});

describe('formatDelta', () => {
  it('renders a dash for null', () => {
    expect(formatDelta(null)).toBe('—');
  });
  it('renders a signed number', () => {
    expect(formatDelta(0.5)).toBe('+0.5');
    expect(formatDelta(-0.25)).toBe('-0.25');
  });
});
