import { firstLine, parseSlackMessage, parseTopSensors, topSensorsText } from './format'

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
  it('parses structured top sensors', () => {
    expect(parseTopSensors(['TP2', 'H1'])).toEqual([
      { name: 'TP2', val: null },
      { name: 'H1', val: null },
    ])
    expect(parseTopSensors({ TP2_mean: 3.2 })).toEqual([
      { name: 'TP2_mean', val: '3.20' },
    ])
    expect(parseTopSensors('TP2_mean (3.2), H1 (1.5)')).toEqual([
      { name: 'TP2_mean', val: '3.2' },
      { name: 'H1', val: '1.5' },
    ])
    expect(parseTopSensors(null)).toEqual([])
  })
  it('parses multi-line Slack alert message', () => {
    const raw = `:rotating_light: *CRITICAL: anomaly and elevated failure risk*
*Time (UTC):* 2020-06-05 10:10    *Severity:* critical
*Failure risk:* 1.00 (threshold 0.50)    *Anomaly score:* 0.69 (threshold 0.67)
*1 likely cause:* DV_pressure mean (5.8 std from normal)
*Suggested action:* Inspect air circuit
<http://localhost:5173/?end=2020-06-05T10:10:00Z|Open the dashboard at this time>`

    const parsed = parseSlackMessage(raw, 'critical')
    expect(parsed.emoji).toBe('🚨')
    expect(parsed.title).toBe('CRITICAL: anomaly and elevated failure risk')
    expect(parsed.scores).toEqual([
      'Failure risk: 1.00 (threshold 0.50)',
      'Anomaly score: 0.69 (threshold 0.67)',
    ])
    expect(parsed.causes).toBe('DV_pressure mean (5.8 std from normal)')
    expect(parsed.action).toBe('Inspect air circuit')
    expect(parsed.linkUrl).toBe('http://localhost:5173/?end=2020-06-05T10:10:00Z')
  })
  it('parses recovery message', () => {
    const raw = `:white_check_mark: *Back to normal*
*Incident:* 2020-06-05 06:50 to 2020-06-05 09:40 UTC (2 h 50 min)
<http://localhost:5173/?end=2020-06-05T09:40:00Z|Open the dashboard at this time>`

    const parsed = parseSlackMessage(raw, 'info')
    expect(parsed.emoji).toBe('✅')
    expect(parsed.title).toBe('Back to normal')
    expect(parsed.incident).toBe('2020-06-05 06:50 to 2020-06-05 09:40 UTC (2 h 50 min)')
  })
})
