import { firstLine, topSensorsText } from './format'

describe('alert text helpers', () => {
  it('takes the first line and removes Slack formatting', () => {
    expect(firstLine(':rotating_light: *CRITICAL: anomaly*\nmore text')).toBe('CRITICAL: anomaly')
    expect(firstLine('plain')).toBe('plain')
    expect(firstLine(null)).toBe('–')
    expect(firstLine(':warning:')).toBe('–')
  })
  it('shows top sensors from lists, objects and text', () => {
    expect(topSensorsText(['TP2', 'H1'])).toBe('TP2, H1')
    expect(topSensorsText({ TP2_mean: 3.2 })).toBe('TP2_mean (3.2)')
    expect(topSensorsText(null)).toBe('–')
  })
})
