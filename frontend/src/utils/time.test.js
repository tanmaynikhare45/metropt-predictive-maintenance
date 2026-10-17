import { bucketFor } from './sensors'
import { fmtFull, fmtNum, shiftIso, tickFormatterFor, toMs } from './time'

describe('time helpers', () => {
  it('formats in UTC', () => {
    expect(fmtFull(toMs('2020-06-05T10:00:00Z'))).toBe('2020-06-05 10:00 UTC')
    expect(fmtFull(null)).toBe('–')
  })
  it('shifts an ISO time', () => {
    expect(shiftIso('2020-06-05T10:00:00+00:00', -3)).toBe('2020-06-05T07:00:00.000Z')
  })
  it('chooses tick format by span', () => {
    const t = toMs('2020-06-05T10:30:00Z')
    expect(tickFormatterFor(2 * 3600 * 1000)(t)).toBe('10:30')
    expect(tickFormatterFor(72 * 3600 * 1000)(t)).toBe('06-05 10:30')
  })
  it('formats numbers and missing values', () => {
    expect(fmtNum(0.123456)).toBe('0.123')
    expect(fmtNum(null)).toBe('–')
  })
  it('keeps sensor charts under about 300 points', () => {
    for (const h of [1, 2, 6, 12, 24]) expect((h * 60) / bucketFor(h)).toBeLessThanOrEqual(300)
  })
})
