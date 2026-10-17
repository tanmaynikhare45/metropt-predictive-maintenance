import { useMemo, useState } from 'react'
import { Area, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { getForecast } from '../api'
import usePolling from '../hooks/usePolling'
import { buildForecastSeries } from '../utils/forecast'
import { fmtFull, fmtNum, tickFormatterFor } from '../utils/time'
import Card from './Card'
import { axisProps, COLORS, tooltipProps } from './chartTheme'

export default function ForecastChart({ end, refreshMs, config, className }) {
  const sensors = config?.forecast_sensors || ['TP2', 'Oil_temperature']
  const [sensor, setSensor] = useState(sensors[0])
  const { data, error, loading } = usePolling(() => getForecast({ sensor, end }), [sensor, end], refreshMs)

  const { rows, nowT } = useMemo(() => buildForecastSeries(data), [data])
  const tMin = rows.length ? rows[0].t : 0
  const tMax = rows.length ? rows[rows.length - 1].t : 0

  const controls = (
    <div className="seg" role="group" aria-label="Forecast sensor">
      {sensors.map((s) => (
        <button key={s} className={s === sensor ? 'on' : ''} onClick={() => setSensor(s)}>{s}</button>
      ))}
    </div>
  )

  return (
    <Card
      className={className}
      title="Forecast"
      subtitle={data ? `Next ${data.forecast.length / 6} h · ${Math.round((config?.forecast_interval ?? 0.9) * 100)}% band · method: ${data.method}` : 'Next 6 hours with a confidence band'}
      right={controls}
      loading={loading && !data}
      loadingText="Fitting the forecast model… (the first request can take about 10 seconds)"
      error={error}
      empty={!loading && rows.length === 0}
      emptyText="No forecast available for this time."
    >
      <div className="chart" style={{ height: 260 }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={rows} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
            <CartesianGrid stroke={COLORS.grid} vertical={false} />
            <XAxis dataKey="t" type="number" scale="time" domain={['dataMin', 'dataMax']} tickFormatter={tickFormatterFor(tMax - tMin)} {...axisProps} />
            <YAxis domain={['auto', 'auto']} tickFormatter={(v) => fmtNum(v, 1)} width={44} {...axisProps} />
            <Tooltip
              {...tooltipProps}
              labelFormatter={(t) => fmtFull(t)}
              formatter={(v, name) => (Array.isArray(v) ? [`${fmtNum(v[0], 2)} to ${fmtNum(v[1], 2)}`, 'band'] : [fmtNum(v, 3), name])}
            />
            <Area dataKey="band" stroke="none" fill={COLORS.forecast} fillOpacity={0.22} isAnimationActive={false} />
            <Line dataKey="hist" name="actual" stroke={COLORS.line} dot={false} strokeWidth={1.6} isAnimationActive={false} connectNulls={false} />
            <Line dataKey="yhat" name="forecast" stroke={COLORS.forecast} dot={false} strokeWidth={1.8} strokeDasharray="5 3" isAnimationActive={false} connectNulls={false} />
            {nowT != null && <ReferenceLine x={nowT} stroke={COLORS.axis} strokeDasharray="3 3" label={{ value: 'now', fill: COLORS.text, fontSize: 11, position: 'insideTopLeft' }} />}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </Card>
  )
}
