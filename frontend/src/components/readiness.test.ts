import { describe, expect, it } from 'vitest';
import { highlightRuns } from './ReadinessWorkbench';
import { validateTherapy } from './TherapyAnswerForm';

describe('highlightRuns', () => {
  it('splits text into plain and highlighted runs by UTF-16 offsets', () => {
    const t = 'ألم 🙂 physiotherapy 8 sessions';
    const s = t.indexOf('physio');
    const runs = highlightRuns(t, [{ start: s, end: s + 'physiotherapy'.length }]);
    expect(runs.map((r) => r.text).join('')).toBe(t);
    expect(runs.find((r) => r.hit)?.text).toBe('physiotherapy');
  });

  it('merges overlapping ranges and ignores empty ones', () => {
    const runs = highlightRuns('abcdefgh', [{ start: 2, end: 5 }, { start: 4, end: 6 }, { start: 7, end: 7 }]);
    expect(runs).toEqual([
      { text: 'ab', hit: false },
      { text: 'cde', hit: true },
      { text: 'f', hit: true },
      { text: 'gh', hit: false },
    ]);
  });
});

describe('validateTherapy (decision D1)', () => {
  it('accepts a complete answer that ends before the request', () => {
    expect(validateTherapy('2026-06-01', '2026-07-20', 8, 'Demo Physio', '2026-08-12')).toBeNull();
  });
  it.each([
    ['', '2026-07-20', 8, 'P', 'Start and end dates are required'],
    ['2026-07-20', '2026-06-01', 8, 'P', 'End date must be after start date'],
    ['2026-07-01', '2026-09-01', 8, 'Demo', 'Therapy must have ended on or before the request date'],
    ['2026-06-01', '2026-07-20', 0, 'Demo', 'Sessions must be between 1 and 60'],
    ['2026-06-01', '2026-07-20', 8, ' ', 'Provider is required'],
  ])('rejects %s → %s', (s, e, n, p, msg) => {
    expect(validateTherapy(s as string, e as string, n as number, p as string, '2026-08-12')).toBe(msg);
  });
});
