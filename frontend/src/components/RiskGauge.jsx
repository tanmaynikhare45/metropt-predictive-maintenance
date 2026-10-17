import { riskLevel } from '../utils/status'

const R = 80
const CX = 100
const CY = 100

// value 0 -> far left, 1 -> far right, going over the top
const point = (v, r = R) => {
  const a = Math.PI * (1 - v)
  return [CX + r * Math.cos(a), CY - r * Math.sin(a)]
}
const arc = (v1, v2) => {
  const [x1, y1] = point(v1)
  const [x2, y2] = point(v2)
  return `M ${x1.toFixed(2)} ${y1.toFixed(2)} A ${R} ${R} 0 0 1 ${x2.toFixed(2)} ${y2.toFixed(2)}`
}

export default function RiskGauge({ value, threshold }) {
  const thr = Math.min(Math.max(threshold ?? 0.5, 0.1), 0.95)
  const v = value == null ? null : Math.min(Math.max(value, 0), 1)
  const level = riskLevel(v, thr)
  const [nx, ny] = v == null ? [CX, CY] : point(v, 66)

  return (
    <svg viewBox="0 0 200 128" className="gauge" role="img" aria-label={`Failure risk ${v == null ? 'unknown' : Math.round(v * 100) + ' percent'}`}>
      <path d={arc(0, thr / 2)} className="seg-healthy" />
      <path d={arc(thr / 2, thr)} className="seg-watch" />
      <path d={arc(thr, 1)} className="seg-alert" />
      {v != null && (
        <>
          <line x1={CX} y1={CY} x2={nx} y2={ny} className="needle" />
          <circle cx={CX} cy={CY} r="5" className="needle-hub" />
        </>
      )}
      <text x={CX} y={CY + 26} textAnchor="middle" className={`gauge-value lvl-${level}`}>
        {v == null ? '–' : `${(v * 100).toFixed(0)}%`}
      </text>
    </svg>
  )
}
