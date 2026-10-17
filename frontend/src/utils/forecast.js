import { toMs } from './time'

// Merge the real history and the forecast into one series for the chart.
export function buildForecastSeries(data) {
  if (!data) return { rows: [], nowT: null }
  const hist = (data.history || []).map((h) => ({ t: toMs(h.time), hist: h.value }))
  const fc = (data.forecast || []).map((f) => ({ t: toMs(f.time), yhat: f.yhat, band: [f.lower, f.upper] }))
  const last = hist[hist.length - 1]
  // start the forecast line at the last real value so the two lines connect
  if (last && fc.length) fc.unshift({ t: last.t, yhat: last.hist, band: [last.hist, last.hist] })
  return { rows: [...hist, ...fc], nowT: last ? last.t : null }
}
