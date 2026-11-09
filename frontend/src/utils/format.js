export function firstLine(value) {
  if (value == null || value === '') return '–'

  const line = String(value).split(/\r?\n/)[0].trim()
  if (!line) return '–'

  const text = line
    .replace(/:[A-Za-z0-9_+-]+:/g, '')
    .replace(/[*_~`]/g, '')
    .replace(/\s+/g, ' ')
    .trim()

  return text || '–'
}

// top_sensors comes from a JSONB column: it can be a list, an object {feature: score} or text
export function topSensorsText(value) {
  if (!value) return '–'
  if (Array.isArray(value)) return value.join(', ')
  if (typeof value === 'object') {
    return Object.entries(value)
      .map(([k, v]) => `${k}${typeof v === 'number' ? ` (${v})` : ''}`)
      .join(', ')
  }
  return String(value)
}
