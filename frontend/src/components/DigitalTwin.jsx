/**
 * DigitalTwin – live sensor dashboard styled as a compressor schematic.
 *
 * Layout:
 *   Left  – SVG schematic with sensor values overlaid on the diagram
 *   Right – gauge bars for analog sensors + LED grid for digital sensors
 *
 * Data comes from the existing /latest endpoint (already polled by App).
 */
import { useMemo } from 'react'
import { fmtNum } from '../utils/time'
import Card from './Card'

// ─── sensor metadata ────────────────────────────────────────────────────────

const ANALOG = [
  { key: 'tp2',            label: 'TP2',           unit: 'bar',  min: 0,   max: 11,  warn: 7,   alert: 9,   desc: 'Delivery pressure' },
  { key: 'tp3',            label: 'TP3',            unit: 'bar',  min: 0,   max: 11,  warn: 7,   alert: 9,   desc: 'Primary circuit pressure' },
  { key: 'h1',             label: 'H1',             unit: 'bar',  min: 0,   max: 11,  warn: 7,   alert: 9,   desc: 'Pneumatic panel pressure' },
  { key: 'dv_pressure',    label: 'DV Pressure',    unit: 'bar',  min: 0,   max: 11,  warn: 7,   alert: 9,   desc: 'Electropneumatic pressure' },
  { key: 'reservoirs',     label: 'Reservoirs',     unit: 'bar',  min: 0,   max: 11,  warn: 7,   alert: 9,   desc: 'Air tank pressure' },
  { key: 'oil_temperature',label: 'Oil Temp',       unit: '°C',   min: 20,  max: 100, warn: 65,  alert: 80,  desc: 'Compressor oil temperature' },
  { key: 'motor_current',  label: 'Motor Current',  unit: 'A',    min: 0,   max: 30,  warn: 18,  alert: 24,  desc: 'Motor current draw' },
]

const DIGITAL = [
  { key: 'comp',            label: 'COMP',           desc: 'Compressor cycling',    activeColor: '#22c55e' },
  { key: 'dv_eletric',     label: 'DV Electric',    desc: 'Electrical valve state', activeColor: '#38bdf8' },
  { key: 'towers',         label: 'Towers',          desc: 'Drying towers valve',    activeColor: '#38bdf8' },
  { key: 'mpg',            label: 'MPG',             desc: 'Condensate drain',       activeColor: '#a78bfa' },
  { key: 'lps',            label: 'LPS',             desc: 'Low pressure switch',    activeColor: '#f59e0b' },
  { key: 'pressure_switch',label: 'Pressure Sw.',    desc: 'Pressure switch',        activeColor: '#f59e0b' },
  { key: 'oil_level',      label: 'Oil Level',       desc: 'Oil level switch',       activeColor: '#22c55e' },
  { key: 'caudal_impulses',label: 'Flow Pulses',     desc: 'Caudal impulse count',   activeColor: '#38bdf8' },
]

// ─── helpers ─────────────────────────────────────────────────────────────────

function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)) }

function sensorLevel(value, s) {
  if (value == null) return 'unknown'
  if (value >= s.alert) return 'alert'
  if (value >= s.warn)  return 'warn'
  return 'ok'
}

const LEVEL_COLORS = { ok: '#22c55e', warn: '#f59e0b', alert: '#ef4444', unknown: '#475569' }

// ─── sub-components ──────────────────────────────────────────────────────────

function BarGauge({ meta, value }) {
  const pct  = value != null ? clamp((value - meta.min) / (meta.max - meta.min), 0, 1) : 0
  const level = sensorLevel(value, meta)
  const color = LEVEL_COLORS[level]
  const warnPct  = (meta.warn  - meta.min) / (meta.max - meta.min)
  const alertPct = (meta.alert - meta.min) / (meta.max - meta.min)

  return (
    <div className="twin-gauge">
      <div className="twin-gauge-header">
        <span className="twin-gauge-label">{meta.label}</span>
        <span className="twin-gauge-value" style={{ color }}>
          {value != null ? `${fmtNum(value, 2)} ${meta.unit}` : '–'}
        </span>
      </div>
      <div className="twin-gauge-track">
        {/* zone ticks */}
        <div className="twin-gauge-tick warn"  style={{ left: `${warnPct  * 100}%` }} />
        <div className="twin-gauge-tick alert" style={{ left: `${alertPct * 100}%` }} />
        {/* fill */}
        <div className="twin-gauge-fill" style={{ width: `${pct * 100}%`, background: color }} />
      </div>
      <div className="twin-gauge-desc">{meta.desc}</div>
    </div>
  )
}

function Led({ meta, value }) {
  const active = value != null && value > 0
  const color  = active ? meta.activeColor : '#1f2a40'
  const textColor = active ? meta.activeColor : '#475569'
  return (
    <div className="twin-led" title={meta.desc}>
      <div className="twin-led-dot" style={{ background: color, boxShadow: active ? `0 0 8px ${meta.activeColor}88` : 'none' }} />
      <div>
        <div className="twin-led-label" style={{ color: textColor }}>{meta.label}</div>
        <div className="twin-led-state">{value == null ? 'N/A' : (active ? 'ON' : 'OFF')}</div>
      </div>
    </div>
  )
}

// ─── SVG schematic ───────────────────────────────────────────────────────────
// A simplified top-down flow diagram of the Metro-PT compressor system.
// Sensor readings are overlaid as floating labels on the relevant components.

function SensorTag({ x, y, label, value, unit, level, align = 'left' }) {
  const color = LEVEL_COLORS[level ?? 'unknown']
  const textAnchor = align === 'right' ? 'end' : 'start'
  const xOff = align === 'right' ? -8 : 8

  return (
    <g>
      <circle cx={x} cy={y} r={4} fill={color} />
      <text x={x + xOff} y={y - 5} textAnchor={textAnchor} fill={color} fontSize={10} fontWeight="600">
        {label}
      </text>
      <text x={x + xOff} y={y + 8} textAnchor={textAnchor} fill={color} fontSize={9}>
        {value != null ? `${fmtNum(value, 2)} ${unit}` : '–'}
      </text>
    </g>
  )
}

function DigitalTag({ x, y, label, value, color }) {
  const active = value != null && value > 0
  const c = active ? color : '#475569'
  return (
    <g>
      <rect x={x - 20} y={y - 10} width={40} height={20} rx={4}
            fill={active ? `${color}22` : '#1f2a40'} stroke={c} strokeWidth={1} />
      <text x={x} y={y + 4} textAnchor="middle" fill={c} fontSize={9} fontWeight="600">{label}</text>
    </g>
  )
}

function Schematic({ sensors }) {
  const s = sensors || {}
  const tp2Level  = sensorLevel(s.tp2,            ANALOG[0])
  const tp3Level  = sensorLevel(s.tp3,            ANALOG[1])
  const h1Level   = sensorLevel(s.h1,             ANALOG[2])
  const dvpLevel  = sensorLevel(s.dv_pressure,    ANALOG[3])
  const resLevel  = sensorLevel(s.reservoirs,     ANALOG[4])
  const oilLevel_ = sensorLevel(s.oil_temperature, ANALOG[5])
  const curLevel  = sensorLevel(s.motor_current,  ANALOG[6])

  return (
    <svg viewBox="0 0 540 320" style={{ width: '100%', height: 'auto', display: 'block' }}>
      <defs>
        <marker id="arr" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto">
          <path d="M0,0 L6,3 L0,6 Z" fill="#38bdf8" />
        </marker>
      </defs>

      {/* ── background ── */}
      <rect width="540" height="320" rx="10" fill="#0b1220" />
      <text x="270" y="20" textAnchor="middle" fill="#94a3b8" fontSize={11} fontWeight="600" letterSpacing="1">
        AIR COMPRESSOR SYSTEM — LIVE SENSOR OVERVIEW
      </text>

      {/* ── motor / compressor block ── */}
      <rect x="30" y="50" width="110" height="70" rx="8" fill="#111a2c" stroke="#1f2a40" strokeWidth="1.5" />
      <text x="85" y="80" textAnchor="middle" fill="#94a3b8" fontSize={10}>MOTOR</text>
      <text x="85" y="96" textAnchor="middle" fill="#94a3b8" fontSize={10}>COMPRESSOR</text>
      {/* comp LED */}
      <circle cx="85" cy="112" r="5" fill={s.comp > 0 ? '#22c55e' : '#1f2a40'}
              stroke={s.comp > 0 ? '#22c55e' : '#475569'} strokeWidth={1}/>
      <text x="96" y="116" fill={s.comp > 0 ? '#22c55e' : '#475569'} fontSize={8}>{s.comp > 0 ? 'RUNNING' : 'IDLE'}</text>

      {/* ── motor current sensor tag ── */}
      <SensorTag x={30} y={148} label="Motor Current" value={s.motor_current} unit="A" level={curLevel} />

      {/* ── oil reservoir ── */}
      <rect x="30" y="175" width="110" height="55" rx="8" fill="#111a2c" stroke="#1f2a40" strokeWidth="1.5" />
      <text x="85" y="197" textAnchor="middle" fill="#94a3b8" fontSize={10}>OIL SYSTEM</text>
      <SensorTag x={40} y={218} label="Oil Temp" value={s.oil_temperature} unit="°C" level={oilLevel_} />
      {/* oil level LED */}
      <circle cx="118" cy="195" r="4" fill={s.oil_level > 0 ? '#22c55e' : '#ef4444'}
              stroke={s.oil_level > 0 ? '#22c55e' : '#ef4444'} strokeWidth={1} />
      <text x="130" y="198" fill={s.oil_level > 0 ? '#22c55e' : '#ef4444'} fontSize={8}>{s.oil_level > 0 ? 'OK' : 'LOW'}</text>

      {/* ── flow pipes from compressor ── */}
      {/* compressor → TP2 pressure sensor */}
      <line x1="140" y1="85" x2="195" y2="85" stroke="#38bdf8" strokeWidth="2" markerEnd="url(#arr)" />

      {/* ── TP2 delivery pressure ── */}
      <rect x="195" y="60" width="85" height="50" rx="8" fill="#111a2c" stroke="#1f2a40" strokeWidth="1.5" />
      <text x="237" y="82" textAnchor="middle" fill="#94a3b8" fontSize={10}>DELIVERY</text>
      <SensorTag x={204} y={102} label="TP2" value={s.tp2} unit="bar" level={tp2Level} />

      {/* TP2 → dryer towers */}
      <line x1="280" y1="85" x2="335" y2="85" stroke="#38bdf8" strokeWidth="2" markerEnd="url(#arr)" />

      {/* ── dryer towers ── */}
      <rect x="335" y="50" width="90" height="70" rx="8" fill="#111a2c" stroke="#1f2a40" strokeWidth="1.5" />
      <text x="380" y="80" textAnchor="middle" fill="#94a3b8" fontSize={10}>AIR DRYER</text>
      <text x="380" y="96" textAnchor="middle" fill="#94a3b8" fontSize={10}>TOWERS</text>
      {/* towers LED */}
      <circle cx="380" cy="112" r="5" fill={s.towers > 0 ? '#38bdf8' : '#1f2a40'}
              stroke={s.towers > 0 ? '#38bdf8' : '#475569'} strokeWidth={1} />
      <text x="391" y="116" fill={s.towers > 0 ? '#38bdf8' : '#475569'} fontSize={8}>{s.towers > 0 ? 'ACTIVE' : 'IDLE'}</text>

      {/* towers → TP3 */}
      <line x1="425" y1="85" x2="480" y2="85" stroke="#38bdf8" strokeWidth="2" markerEnd="url(#arr)" />
      <SensorTag x={488} y={85} label="TP3" value={s.tp3} unit="bar" level={tp3Level} />

      {/* ── dryer → reservoirs (vertical) ── */}
      <line x1="380" y1="120" x2="380" y2="160" stroke="#38bdf8" strokeWidth="2" markerEnd="url(#arr)" />

      {/* ── air reservoir tanks ── */}
      <rect x="335" y="160" width="90" height="55" rx="8" fill="#111a2c" stroke="#1f2a40" strokeWidth="1.5" />
      <text x="380" y="180" textAnchor="middle" fill="#94a3b8" fontSize={10}>RESERVOIR</text>
      <text x="380" y="196" textAnchor="middle" fill="#94a3b8" fontSize={10}>TANKS</text>
      <SensorTag x={432} y={200} label="Reservoirs" value={s.reservoirs} unit="bar" level={resLevel} align="left" />

      {/* ── LPS on reservoir ── */}
      <circle cx="336" cy="178" r="5" fill={s.lps > 0 ? '#f59e0b' : '#1f2a40'}
              stroke={s.lps > 0 ? '#f59e0b' : '#475569'} strokeWidth={1} />
      <text x="323" y="175" textAnchor="end" fill={s.lps > 0 ? '#f59e0b' : '#475569'} fontSize={8}>LPS</text>

      {/* ── reservoir → panel (H1) ── */}
      <line x1="335" y1="187" x2="280" y2="187" stroke="#38bdf8" strokeWidth="2" markerEnd="url(#arr)" />

      {/* ── pneumatic panel ── */}
      <rect x="195" y="160" width="85" height="55" rx="8" fill="#111a2c" stroke="#1f2a40" strokeWidth="1.5" />
      <text x="237" y="181" textAnchor="middle" fill="#94a3b8" fontSize={10}>PNEUM.</text>
      <text x="237" y="197" textAnchor="middle" fill="#94a3b8" fontSize={10}>PANEL</text>
      <SensorTag x={195} y={225} label="H1" value={s.h1} unit="bar" level={h1Level} />

      {/* ── H1 panel → DV pressure valve ── */}
      <line x1="237" y1="215" x2="237" y2="260" stroke="#38bdf8" strokeWidth="2" markerEnd="url(#arr)" />

      {/* ── DV electropneumatic valve ── */}
      <rect x="195" y="260" width="85" height="50" rx="8" fill="#111a2c" stroke="#1f2a40" strokeWidth="1.5" />
      <text x="237" y="280" textAnchor="middle" fill="#94a3b8" fontSize={10}>DV VALVE</text>
      {/* dv_electric LED */}
      <circle cx="210" cy="295" r="4" fill={s.dv_eletric > 0 ? '#38bdf8' : '#1f2a40'}
              stroke={s.dv_eletric > 0 ? '#38bdf8' : '#475569'} strokeWidth={1} />
      <text x="220" y="298" fill={s.dv_eletric > 0 ? '#38bdf8' : '#475569'} fontSize={8}>{s.dv_eletric > 0 ? 'OPEN' : 'CLOSED'}</text>
      <SensorTag x={280} y={285} label="DV Press." value={s.dv_pressure} unit="bar" level={dvpLevel} />

      {/* ── MPG drain + pressure switch ── */}
      <line x1="237" y1="310" x2="237" y2="318" stroke="#38bdf8" strokeWidth="1.5" />
      <DigitalTag x={100} y={270} label="MPG" value={s.mpg} color="#a78bfa" />
      <DigitalTag x={100} y={300} label="P.SW" value={s.pressure_switch} color="#f59e0b" />
      <DigitalTag x={100} y={245} label="FLOW" value={s.caudal_impulses} color="#38bdf8" />

      {/* ── flow line from compressor to MPG area ── */}
      <line x1="140" y1="230" x2="80" y2="230" stroke="#38bdf8" strokeWidth="1.5" strokeDasharray="4 3" />
    </svg>
  )
}

// ─── Health Index ─────────────────────────────────────────────────────────────

function HealthIndex({ sensors }) {
  const s = sensors || {}
  const scores = ANALOG.map(m => {
    const v = s[m.key]
    if (v == null) return null
    const level = sensorLevel(v, m)
    if (level === 'alert') return 0
    if (level === 'warn')  return 0.5
    return 1
  }).filter(x => x !== null)

  const index = scores.length ? Math.round((scores.reduce((a, b) => a + b, 0) / scores.length) * 100) : null
  const color = index == null ? '#475569' : index >= 80 ? '#22c55e' : index >= 50 ? '#f59e0b' : '#ef4444'
  const label = index == null ? 'No data' : index >= 80 ? 'Healthy' : index >= 50 ? 'Degraded' : 'Critical'

  return (
    <div className="twin-health">
      <div className="twin-health-label">System Health Index</div>
      <div className="twin-health-value" style={{ color }}>{index != null ? `${index}%` : '–'}</div>
      <div className="twin-health-state" style={{ color }}>{label}</div>
      <div className="twin-health-track">
        <div className="twin-health-fill" style={{ width: `${index ?? 0}%`, background: color }} />
      </div>
    </div>
  )
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function DigitalTwin({ className, latest, loading, error }) {
  const sensors = latest?.sensors || null

  const time = useMemo(() => {
    if (!sensors?.time) return null
    return new Date(sensors.time).toUTCString().replace('GMT', 'UTC')
  }, [sensors?.time])

  return (
    <Card
      className={className}
      title="Digital Twin"
      subtitle={time ? `Live sensor snapshot · ${time}` : 'Live sensor snapshot · waiting for data…'}
      loading={loading && !latest}
      error={error}
    >
      <div className="twin-layout">
        {/* ── left: schematic ── */}
        <div className="twin-schematic">
          <Schematic sensors={sensors} />
        </div>

        {/* ── right: gauges + LEDs ── */}
        <div className="twin-panels">
          <HealthIndex sensors={sensors} />

          <div className="twin-section-title">Analog Sensors</div>
          <div className="twin-gauges">
            {ANALOG.map(m => (
              <BarGauge key={m.key} meta={m} value={sensors?.[m.key]} />
            ))}
          </div>

          <div className="twin-section-title" style={{ marginTop: 14 }}>Digital Signals</div>
          <div className="twin-leds">
            {DIGITAL.map(m => (
              <Led key={m.key} meta={m} value={sensors?.[m.key]} />
            ))}
          </div>
        </div>
      </div>
    </Card>
  )
}

