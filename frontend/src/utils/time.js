// Everything is shown in UTC: the dataset is historic and its timestamps have no local meaning.
export const toMs = (iso) => new Date(iso).getTime()

const iso = (ms) => new Date(ms).toISOString()

export const fmtFull = (ms) => (ms == null || Number.isNaN(ms) ? '–' : `${iso(ms).slice(0, 16).replace('T', ' ')} UTC`)

export const fmtClock = (ms) => iso(ms).slice(11, 16)

// axis ticks: "10:30" for short ranges, "06-05 10:30" for longer ones
export const tickFormatterFor = (spanMs) => (ms) =>
  spanMs > 30 * 3600 * 1000 ? `${iso(ms).slice(5, 10)} ${iso(ms).slice(11, 16)}` : iso(ms).slice(11, 16)

export const fmtNum = (v, digits = 3) => (v == null || Number.isNaN(Number(v)) ? '–' : Number(v).toFixed(digits))

// ISO string shifted by N hours (returns an ISO string with Z)
export const shiftIso = (isoString, hours) => iso(toMs(isoString) + hours * 3600 * 1000)
