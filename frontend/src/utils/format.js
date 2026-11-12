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

export function parseTopSensors(value) {
  if (!value) return []
  if (Array.isArray(value)) {
    return value.map((v) => ({ name: String(v), val: null }))
  }
  if (typeof value === 'object') {
    return Object.entries(value).map(([k, v]) => ({
      name: k,
      val: typeof v === 'number' ? v.toFixed(2) : String(v),
    }))
  }
  return String(value)
    .split(',')
    .map((s) => {
      const trimmed = s.trim()
      const match = trimmed.match(/^([^(]+)(?:\(([^)]+)\))?$/)
      if (match) {
        return { name: match[1].trim(), val: match[2]?.trim() || null }
      }
      return { name: trimmed, val: null }
    })
    .filter((x) => Boolean(x.name))
}

const EMOJI_MAP = {
  ':rotating_light:': '🚨',
  ':warning:': '⚠️',
  ':white_check_mark:': '✅',
  ':hourglass_flowing_sand:': '⏳',
  ':x:': '❌',
  ':info:': 'ℹ️',
}

const SEVERITY_EMOJI = {
  critical: '🚨',
  warning: '⚠️',
  info: 'ℹ️',
}

export function parseSlackMessage(text, severity = null) {
  if (!text) return null

  const rawLines = String(text)
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean)
  if (rawLines.length === 0) return null

  let emoji = null
  let title = ''
  let incident = null
  let ongoing = null
  const scores = []
  let causes = null
  let action = null
  let linkUrl = null
  const otherLines = []

  let line0 = rawLines[0]
  for (const [code, sym] of Object.entries(EMOJI_MAP)) {
    if (line0.includes(code)) {
      emoji = sym
      line0 = line0.replace(code, '').trim()
    }
  }
  title = line0.replace(/^\*+|\*+$/g, '').trim()

  if (!emoji && severity && SEVERITY_EMOJI[severity]) {
    emoji = SEVERITY_EMOJI[severity]
  }

  for (let i = 1; i < rawLines.length; i++) {
    const line = rawLines[i]

    // Skip redundant Time & Severity line since the table has separate columns
    if (/^\*Time\s*\(UTC\):\*/i.test(line)) {
      continue
    }

    if (/^\*Incident:\*/i.test(line)) {
      incident = line.replace(/^\*Incident:\*\s*/i, '').replace(/\*/g, '').trim()
      continue
    }

    if (/^\*Ongoing since:\*/i.test(line)) {
      ongoing = line.replace(/^\*Ongoing since:\*\s*/i, '').replace(/\*/g, '').trim()
      continue
    }

    if (/^\*(?:[0-9]+\s+)?likely causes?:\*/i.test(line)) {
      causes = line.replace(/^\*(?:[0-9]+\s+)?likely causes?:\*\s*/i, '').replace(/\*/g, '').trim()
      continue
    }

    if (/^\*Suggested action:\*/i.test(line)) {
      action = line.replace(/^\*Suggested action:\*\s*/i, '').replace(/\*/g, '').trim()
      continue
    }

    const linkMatch = line.match(/<(https?:\/\/[^|>]+)\|([^>]+)>/)
    if (linkMatch) {
      linkUrl = linkMatch[1]
      continue
    }

    if (line.includes('Failure risk') || line.includes('Anomaly score')) {
      const parts = line.split(/\s{2,}|\t+/).filter(Boolean)
      scores.push(...parts.map((p) => p.replace(/\*/g, '').trim()))
      continue
    }

    otherLines.push(line.replace(/\*/g, '').trim())
  }

  return {
    emoji: emoji || '🔔',
    title: title || 'Alert',
    incident,
    ongoing,
    scores,
    causes,
    action,
    linkUrl,
    otherLines,
  }
}
