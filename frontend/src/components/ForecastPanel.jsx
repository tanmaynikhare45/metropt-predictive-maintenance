import React, { useState, useEffect } from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { TrendingUp, RefreshCw } from 'lucide-react';
import { getForecast } from '../api';

function ForecastTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;

  return (
    <div style={{
      background: 'var(--tooltip-bg)',
      border: '1px solid var(--tooltip-border)',
      borderRadius: '8px',
      padding: '0.75rem 1rem',
      fontFamily: 'var(--font-sans)',
      fontSize: '0.8rem',
      boxShadow: 'var(--shadow-dropdown)',
      backdropFilter: 'blur(10px)',
      color: 'var(--text-main)',
    }}>
      <div style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', marginBottom: '0.4rem', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.25rem' }}>
        {label ? new Date(label).toUTCString().slice(17, 25) + ' UTC' : ''}
      </div>
      {payload.map((entry, index) => (
        <div key={`fc-${index}`} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem', margin: '0.2rem 0' }}>
          <span style={{ color: entry.color }}>{entry.name}:</span>
          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--text-main)' }}>
            {Number(entry.value).toFixed(2)}
          </span>
        </div>
      ))}
    </div>
  );
}

export default function ForecastPanel() {
  const [sensor, setSensor] = useState('TP2');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchSensorForecast = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getForecast(sensor);
      setData(res);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Forecast model unavailable');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSensorForecast();
  }, [sensor]);

  const combined = [];
  if (data?.history) {
    data.history.slice(-36).forEach((h) => {
      combined.push({
        time: h.time,
        formattedTime: new Date(h.time).toUTCString().slice(17, 22),
        actual: h.value,
      });
    });
  }
  if (data?.forecast) {
    data.forecast.forEach((f) => {
      combined.push({
        time: f.time,
        formattedTime: new Date(f.time).toUTCString().slice(17, 22),
        predicted: f.yhat,
        lower: f.lower,
        upper: f.upper,
      });
    });
  }

  return (
    <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem', marginBottom: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <TrendingUp size={18} color="var(--accent-emerald)" />
            <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.15rem', fontWeight: 600 }}>
              Prophet Time-Series Forecast
            </h2>
          </div>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.1rem' }}>
            6-Hour Forward Horizon with 90% Confidence Interval
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <div style={{ display: 'flex', background: 'var(--bg-secondary)', padding: '3px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <button
              className={`btn-control ${sensor === 'TP2' ? 'active' : ''}`}
              style={{ padding: '0.25rem 0.65rem', fontSize: '0.75rem', border: 'none', boxShadow: 'none' }}
              onClick={() => setSensor('TP2')}
            >
              TP2 Pressure
            </button>
            <button
              className={`btn-control ${sensor === 'Oil_temperature' ? 'active' : ''}`}
              style={{ padding: '0.25rem 0.65rem', fontSize: '0.75rem', border: 'none', boxShadow: 'none' }}
              onClick={() => setSensor('Oil_temperature')}
            >
              Oil Temp
            </button>
          </div>
          <button
            className="btn-control"
            style={{ padding: '0.35rem' }}
            onClick={fetchSensorForecast}
            disabled={loading}
          >
            <RefreshCw size={13} />
          </button>
        </div>
      </div>

      <div style={{ width: '100%', height: 300, position: 'relative' }}>
        {loading && (
          <div style={{
            position: 'absolute', inset: 0, background: 'var(--bg-card)', opacity: 0.8,
            backdropFilter: 'blur(2px)', display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 10, color: 'var(--text-muted)', fontSize: '0.85rem'
          }}>
            Computing forecast...
          </div>
        )}

        {error ? (
          <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-dim)', fontSize: '0.85rem' }}>
            {error}
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <ComposedChart data={combined} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" vertical={false} />
              <XAxis dataKey="formattedTime" stroke="#64748b" fontSize={11} tickLine={false} axisLine={{ stroke: 'var(--border-subtle)' }} />
              <YAxis stroke="#64748b" fontSize={11} domain={['auto', 'auto']} tickLine={false} axisLine={{ stroke: 'var(--border-subtle)' }} />
              <Tooltip content={<ForecastTooltip />} />

              {/* Shaded Confidence Interval */}
              <Area
                type="monotone"
                dataKey="upper"
                stroke="none"
                fill="var(--accent-emerald)"
                fillOpacity={0.16}
                name="Confidence Upper"
              />
              <Area
                type="monotone"
                dataKey="lower"
                stroke="none"
                fill="var(--bg-card)"
                fillOpacity={0.95}
                name="Confidence Lower"
              />

              {/* Past actual */}
              <Line
                type="monotone"
                dataKey="actual"
                name="Historical"
                stroke="var(--accent-cyan)"
                strokeWidth={2}
                dot={false}
              />

              {/* Forecast line */}
              <Line
                type="monotone"
                dataKey="predicted"
                name="Forecast"
                stroke="var(--accent-emerald)"
                strokeWidth={2}
                strokeDasharray="4 4"
                dot={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
