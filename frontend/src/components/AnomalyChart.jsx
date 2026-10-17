import { useMemo, useState } from 'react'
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { getPredictions } from '../api'
import usePolling from '../hooks/usePolling'
import { fmtFull, fmtNum, tickFormatterFor, toMs } from '../utils/time'
import Card from './Card'
import { axisProps, COLORS, failureAreas, tooltipProps } from './chartTheme'

const MODELS = [
  { id: 'iforest', label: 'Isolation Forest', thr: 'iforest_threshold' },
  { id: 'lstm_ae', label: 'LSTM autoencoder', thr: 'lstm_threshold' },
  { id: 'failure_risk', label: 'Failure risk', thr: 'failure_threshold', fixed: [0, 1] },
]
const HOURS = [6, 24, 72]

export default function AnomalyChart({ end, refreshMs, config, failures, className }) {
  const [model, setModel] = useState('iforest')
  const [hours, setHours] = useState(24)
  const meta = MODELS.find((m) => m.id === model)

  const { data, error, loading } = usePolling(() => getPredictions({ model, hours, end }), [model, hours, end], refreshMs)

  const rows = useMemo(() => (data || []).map((d) => ({ t: toMs(d.time), score: d.score, flag: d.flag })), [data])
  const threshold = config?.[meta.thr]
  const flagged = rows.filter((r) => r.flag).length
  const tMin = rows.length ? rows[0].t : null
  const tMax = rows.length ? rows[rows.length - 1].t : null

  const controls = (
    <div className="controls">
      <div className="seg" role="group" aria-label="Model">
        {MODELS.map((m) => (
          <button key={m.id} className={m.id === model ? 'on' : ''} onClick={() => setModel(m.id)}>{m.label}</button>
        ))}
      </div>
      <div className="seg" role="group" aria-label="Hours">
        {HOURS.map((h) => (
          <button key={h} className={h === hours ? 'on' : ''} onClick={() => setHours(h)}>{h} h</button>
        ))}
      </div>
    </div>
  )

  return (
    <Card
      className={className}
      title="Anomaly and risk scores"
      subtitle={rows.length ? `${flagged} of ${rows.length} windows above the threshold · red = known failures` : 'Higher = more unusual'}
      right={controls}
      loading={loading && !data}
      error={error}
      empty={!loading && rows.length === 0}
      emptyText={model === 'lstm_ae' ? 'No LSTM scores stored (run the consumer or backfill with --lstm).' : 'No scores in this time range.'}
    >
      <div className="chart" style={{ height: 260 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
            <CartesianGrid stroke={COLORS.grid} vertical={false} />
            <XAxis dataKey="t" type="number" scale="time" domain={['dataMin', 'dataMax']} tickFormatter={tickFormatterFor((tMax ?? 0) - (tMin ?? 0))} {...axisProps} />
            <YAxis domain={meta.fixed || ['auto', 'auto']} tickFormatter={(v) => fmtNum(v, 2)} width={48} {...axisProps} />
            <Tooltip {...tooltipProps} labelFormatter={(t) => fmtFull(t)} formatter={(v) => [fmtNum(v, 4), 'score']} />
            {failureAreas(failures, tMin, tMax)}
            {threshold != null && <ReferenceLine y={threshold} stroke={COLORS.threshold} strokeDasharray="5 4" label={{ value: 'threshold', fill: COLORS.threshold, fontSize: 11, position: 'insideTopRight' }} />}
            <Line type="monotone" dataKey="score" stroke={COLORS.line} dot={false} strokeWidth={1.5} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  )
}
