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
