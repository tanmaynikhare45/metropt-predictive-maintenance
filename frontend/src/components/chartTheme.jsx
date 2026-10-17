import { ReferenceArea } from 'recharts'
import { toMs } from '../utils/time'

export const COLORS = {
  grid: '#1f2937',
  axis: '#475569',
  text: '#94a3b8',
  line: '#38bdf8',
  threshold: '#f59e0b',
  failure: '#ef4444',
  forecast: '#a78bfa',
}

export const axisProps = { stroke: COLORS.axis, tick: { fill: COLORS.text, fontSize: 11 } }

export const tooltipProps = {
  contentStyle: { background: '#0b1220', border: '1px solid #1f2937', borderRadius: 8, color: '#e5e7eb', fontSize: 12 },
  labelStyle: { color: '#94a3b8' },
}

// Red areas for the known failures that overlap the visible time range.
// (A plain function, not a component: Recharts reads its children directly.)
export function failureAreas(failures, tMin, tMax) {
  if (!failures || tMin == null || tMax == null) return []
  return failures
    .map((f, i) => ({ i, s: toMs(f.start_time), e: toMs(f.end_time) }))
    .filter(({ s, e }) => e >= tMin && s <= tMax)
    .map(({ i, s, e }) => (
      <ReferenceArea
        key={`failure-${i}`}
        x1={Math.max(s, tMin)}
        x2={Math.min(e, tMax)}
        fill={COLORS.failure}
        fillOpacity={0.22}
        stroke="none"
        ifOverflow="hidden"
      />
    ))
}
