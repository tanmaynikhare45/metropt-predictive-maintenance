import React, { useState } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { Activity } from 'lucide-react';

const SENSOR_META = {
  tp2: { label: 'TP2 (Compressor Out)', color: '#38bdf8', unit: 'bar' },
  tp3: { label: 'TP3 (Pneumatic Panel)', color: '#60a5fa', unit: 'bar' },
  reservoirs: { label: 'Main Reservoirs', color: '#34d399', unit: 'bar' },
  motor_current: { label: 'Motor Current', color: '#fbbf24', unit: 'A' },
  oil_temperature: { label: 'Oil Temperature', color: '#f87171', unit: '°C' },
  dv_pressure: { label: 'DV Pressure', color: '#c084fc', unit: 'bar' },
};

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;

  return (
    <div style={{
      background: 'rgba(17, 24, 39, 0.95)',
      border: '1px solid rgba(255, 255, 255, 0.18)',
      borderRadius: '8px',
      padding: '0.75rem 1rem',
      boxShadow: 'var(--shadow-dropdown)',
      fontFamily: 'var(--font-sans)',
      fontSize: '0.8rem',
      backdropFilter: 'blur(10px)',
      color: '#ffffff',
    }}>
      <div style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', marginBottom: '0.4rem', borderBottom: '1px solid rgba(255, 255, 255, 0.1)', paddingBottom: '0.25rem' }}>
        {label ? new Date(label).toUTCString().slice(17, 25) + ' UTC' : ''}
      </div>
      {payload.map((entry, index) => {
        const meta = SENSOR_META[entry.dataKey] || { label: entry.name, unit: '' };
        return (
          <div key={`item-${index}`} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1.25rem', margin: '0.25rem 0' }}>
            <span style={{ color: entry.color, display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: entry.color }} />
              {meta.label}:
            </span>
            <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: '#ffffff' }}>
              {Number(entry.value).toFixed(2)} {meta.unit}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default function SensorTelemetryChart({ data = [], loading = false }) {
  const [activeSensors, setActiveSensors] = useState(['tp2', 'tp3', 'reservoirs', 'motor_current']);

  const toggleSensor = (key) => {
    setActiveSensors((prev) =>
      prev.includes(key) ? (prev.length > 1 ? prev.filter((k) => k !== key) : prev) : [...prev, key]
    );
  };

  const formattedData = (data || []).map((row) => ({
    ...row,
    formattedTime: new Date(row.time).toUTCString().slice(17, 22),
  }));

  return (
    <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column' }}>
      {/* Header and Sensor Filter Pills */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem', marginBottom: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Activity size={18} color="var(--accent-cyan)" />
            <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.15rem', fontWeight: 600 }}>
              Live Sensor Telemetry
            </h2>
          </div>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.1rem' }}>
            Multi-channel analog streams resampled in TimescaleDB hypertable
          </p>
        </div>

        {/* Toggle Pills */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
          {Object.entries(SENSOR_META).map(([key, meta]) => {
            const isActive = activeSensors.includes(key);
            return (
              <button
                key={key}
                onClick={() => toggleSensor(key)}
                style={{
                  background: isActive ? `${meta.color}22` : 'var(--bg-secondary)',
                  color: isActive ? meta.color : 'var(--text-muted)',
                  border: `1px solid ${isActive ? meta.color : 'var(--border-subtle)'}`,
                  borderRadius: '999px',
                  padding: '0.25rem 0.65rem',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.35rem',
                  transition: 'all 0.2s',
                  boxShadow: 'var(--shadow-sm)'
                }}
              >
                <span style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: meta.color }} />
                {meta.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Chart Canvas */}
      <div style={{ width: '100%', height: 300, position: 'relative' }}>
        {loading && (
          <div style={{
            position: 'absolute',
            inset: 0,
            background: 'var(--bg-card)',
            opacity: 0.8,
            backdropFilter: 'blur(2px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 10,
            color: 'var(--text-muted)',
            fontSize: '0.85rem'
          }}>
            Synchronizing data...
          </div>
        )}

        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={formattedData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" vertical={false} />
            <XAxis
              dataKey="formattedTime"
              stroke="var(--chart-axis)"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: 'var(--border-subtle)' }}
            />
            <YAxis
              stroke="var(--chart-axis)"
              fontSize={11}
              domain={['auto', 'auto']}
              tickLine={false}
              axisLine={{ stroke: 'var(--border-subtle)' }}
            />
            <Tooltip content={<CustomTooltip />} />
            {activeSensors.map((key) => {
              const meta = SENSOR_META[key];
              return (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  name={meta.label}
                  stroke={meta.color}
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
              );
            })}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
