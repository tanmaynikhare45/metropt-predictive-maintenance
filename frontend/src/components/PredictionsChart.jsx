import React, { useState } from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from 'recharts';
import { BrainCircuit, AlertOctagon } from 'lucide-react';

function PredictionTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;

  return (
    <div style={{
      background: 'rgba(15, 23, 42, 0.95)',
      border: '1px solid rgba(148, 163, 184, 0.25)',
      borderRadius: '8px',
      padding: '0.75rem 1rem',
      fontFamily: 'var(--font-sans)',
      fontSize: '0.8rem',
      backdropFilter: 'blur(10px)',
    }}>
      <div style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', marginBottom: '0.4rem', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '0.25rem' }}>
        {label ? new Date(label).toUTCString().slice(17, 25) + ' UTC' : ''}
      </div>
      {payload.map((entry, index) => (
        <div key={`pred-${index}`} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem', margin: '0.25rem 0' }}>
          <span style={{ color: entry.color, display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: entry.color }} />
            {entry.name}:
          </span>
          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: '#f8fafc' }}>
            {Number(entry.value).toFixed(3)}
          </span>
        </div>
      ))}
    </div>
  );
}

export default function PredictionsChart({ iforestData = [], failureRiskData = [], threshold = 0.5 }) {
  const [activeModel, setActiveModel] = useState('both'); // 'iforest', 'failure_risk', 'both'

  // Merge the two streams by timestamp
  const mergedMap = new Map();

  (iforestData || []).forEach((row) => {
    const t = row.time;
    mergedMap.set(t, { time: t, if_score: row.score, if_flag: row.flag });
  });

  (failureRiskData || []).forEach((row) => {
    const t = row.time;
    const existing = mergedMap.get(t) || { time: t };
    mergedMap.set(t, { ...existing, risk_score: row.score, risk_flag: row.flag });
  });

  const chartData = Array.from(mergedMap.values())
    .sort((a, b) => new Date(a.time) - new Date(b.time))
    .map((row) => ({
      ...row,
      formattedTime: new Date(row.time).toUTCString().slice(17, 22),
    }));

  return (
    <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem', marginBottom: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <BrainCircuit size={18} color="#a855f7" />
            <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.15rem', fontWeight: 600 }}>
              AI Anomaly & Risk Inference
            </h2>
          </div>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.1rem' }}>
            Unsupervised Isolation Forest + Supervised Leave-One-Out Failure Risk
          </p>
        </div>

        {/* Model Selector Tabs */}
        <div style={{ display: 'flex', background: 'rgba(30, 41, 59, 0.6)', padding: '3px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
          <button
            className={`btn-control ${activeModel === 'both' ? 'active' : ''}`}
            style={{ padding: '0.25rem 0.6rem', fontSize: '0.75rem' }}
            onClick={() => setActiveModel('both')}
          >
            Combined
          </button>
          <button
            className={`btn-control ${activeModel === 'iforest' ? 'active' : ''}`}
            style={{ padding: '0.25rem 0.6rem', fontSize: '0.75rem' }}
            onClick={() => setActiveModel('iforest')}
          >
            Isolation Forest
          </button>
          <button
            className={`btn-control ${activeModel === 'failure_risk' ? 'active' : ''}`}
            style={{ padding: '0.25rem 0.6rem', fontSize: '0.75rem' }}
            onClick={() => setActiveModel('failure_risk')}
          >
            Failure Risk (6h)
          </button>
        </div>
      </div>

      <div style={{ width: '100%', height: 320 }}>
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.08)" vertical={false} />
            <XAxis
              dataKey="formattedTime"
              stroke="#64748b"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: 'rgba(148, 163, 184, 0.15)' }}
            />
            <YAxis
              stroke="#64748b"
              fontSize={11}
              domain={[0, 1]}
              tickLine={false}
              axisLine={{ stroke: 'rgba(148, 163, 184, 0.15)' }}
            />
            <Tooltip content={<PredictionTooltip />} />

            {/* Threshold Line */}
            <ReferenceLine
              y={threshold}
              stroke="#f43f5e"
              strokeDasharray="4 4"
              label={{ value: 'Alert Threshold', fill: '#fb7185', fontSize: 10, position: 'right' }}
            />

            {(activeModel === 'both' || activeModel === 'iforest') && (
              <Line
                type="monotone"
                dataKey="if_score"
                name="Anomaly Score"
                stroke="#c084fc"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            )}

            {(activeModel === 'both' || activeModel === 'failure_risk') && (
              <Area
                type="monotone"
                dataKey="risk_score"
                name="Failure Risk"
                stroke="#38bdf8"
                fill="url(#riskGradient)"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            )}

            <defs>
              <linearGradient id="riskGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#38bdf8" stopOpacity={0.0} />
              </linearGradient>
            </defs>
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
