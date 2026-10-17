import { useMemo, useState } from 'react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { getSensors } from '../api'
import usePolling from '../hooks/usePolling'
import { bucketFor, SENSORS } from '../utils/sensors'
import { fmtFull, fmtNum, tickFormatterFor, toMs } from '../utils/time'
import Card from './Card'
import { axisProps, COLORS, failureAreas, tooltipProps } from './chartTheme'

const HOURS = [1, 2, 6, 12, 24]
export default function SensorChart({ end, refreshMs, failures, className }) {
  const [hours, setHours] = useState(2)
  const [selected, setSelected] = useState(['tp2', 'tp3', 'oil_temperature', 'motor_current'])
  const ordered = SENSORS.filter((s) => selected.includes(s.key))
  const keys = ordered.map((s) => s.key)

  const { data, error, loading } = usePolling(
    () => getSensors({ hours, bucket: bucketFor(hours), sensors: keys, end }),
    [hours, keys.join(','), end],
    refreshMs,
  )

  const rows = useMemo(() => (data || []).map((d) => ({ ...d, t: toMs(d.time) })), [data])
  const tMin = rows.length ? rows[0].t : null
  const tMax = rows.length ? rows[rows.length - 1].t : null

  const toggle = (key) =>
    setSelected((cur) => (cur.includes(key) ? (cur.length > 1 ? cur.filter((k) => k !== key) : cur) : [...cur, key]))

  const controls = (
    <div className="controls">
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
      title="Live sensors"
      subtitle={`Average per ${bucketFor(hours)} min · red = known failures`}
      right={controls}
      loading={loading && !data}
      error={error}
      empty={!loading && rows.length === 0}
      emptyText="No sensor data in this time range."
    >
      <div className="pills" role="group" aria-label="Sensors">
        {SENSORS.map((s) => (
          <button key={s.key} className={`pill ${selected.includes(s.key) ? 'on' : ''}`} onClick={() => toggle(s.key)}>{s.label}</button>
        ))}
      </div>
      <div className="mini-grid">
        {ordered.map((s) => (
          <div className="mini" key={s.key}>
            <div className="mini-title">{s.label}</div>
            <div className="chart" style={{ height: 150 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={rows} margin={{ top: 4, right: 12, bottom: 0, left: 0 }}>
                  <CartesianGrid stroke={COLORS.grid} vertical={false} />
                  <XAxis dataKey="t" type="number" scale="time" domain={['dataMin', 'dataMax']} tickFormatter={tickFormatterFor((tMax ?? 0) - (tMin ?? 0))} {...axisProps} />
                  <YAxis domain={['auto', 'auto']} tickFormatter={(v) => fmtNum(v, 1)} width={44} {...axisProps} />
                  <Tooltip {...tooltipProps} labelFormatter={(t) => fmtFull(t)} formatter={(v) => [fmtNum(v, 3), s.label]} />
                  {failureAreas(failures, tMin, tMax)}
                  <Line type="monotone" dataKey={s.key} stroke={COLORS.line} dot={false} strokeWidth={1.4} isAnimationActive={false} connectNulls={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        ))}
      </div>
    </Card>
  )
}
