import React, { useState } from 'react';
import { Layers, Sliders, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';

export default function DigitalTwinQuickView({ latestSensors = {} }) {
  const [whatIfTempOffset, setWhatIfTempOffset] = useState(0);
  const [whatIfPressureDrop, setWhatIfPressureDrop] = useState(0);

  const rawTemp = latestSensors.oil_temperature || 62.0;
  const rawTP2 = latestSensors.tp2 || 8.8;

  const simTemp = rawTemp + whatIfTempOffset;
  const simTP2 = Math.max(0, rawTP2 - whatIfPressureDrop);

  // Simulated health impact
  const tempPenalty = Math.max(0, (simTemp - 75) * 2.5);
  const pressurePenalty = Math.max(0, whatIfPressureDrop * 15);
  const simHealth = Math.max(10, Math.min(100, Math.round(95 - tempPenalty - pressurePenalty)));

  const components = [
    {
      name: 'Electric Motor',
      role: 'APU Drive Unit',
      value: `${(latestSensors.motor_current || 4.2).toFixed(1)} A`,
      nominal: (latestSensors.motor_current || 4.2) < 9.0,
      icon: '⚡',
    },
    {
      name: 'Air Compressor',
      role: 'Rotary Screw Head',
      value: `${simTP2.toFixed(1)} bar`,
      nominal: simTP2 > 7.5,
      icon: '🌀',
    },
    {
      name: 'Oil Cooling Loop',
      role: 'Thermal Regulation',
      value: `${simTemp.toFixed(1)} °C`,
      nominal: simTemp < 78,
      icon: '❄️',
    },
    {
      name: 'Air Dryer Towers',
      role: 'Moisture Adsorption',
      value: (latestSensors.towers || 0) > 0.5 ? 'Active' : 'Standby',
      nominal: true,
      icon: '🏛️',
    },
    {
      name: 'Main Reservoirs',
      role: 'Pneumatic Storage',
      value: `${(latestSensors.reservoirs || 9.1).toFixed(1)} bar`,
      nominal: (latestSensors.reservoirs || 9.1) > 7.0,
      icon: '🛢️',
    },
  ];

  return (
    <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Layers size={18} color="#38bdf8" />
            <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.15rem', fontWeight: 600 }}>
              Digital Twin & Subsystems
            </h2>
          </div>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.1rem' }}>
            Virtual APU Component States & Interactive What-If Simulator
          </p>
        </div>
        <span className="status-badge nominal">
          SYNCHRONIZED
        </span>
      </div>

      {/* Components Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '0.65rem', marginBottom: '1.25rem' }}>
        {components.map((c, i) => (
          <div
            key={i}
            style={{
              background: 'rgba(30, 41, 59, 0.45)',
              border: `1px solid ${c.nominal ? 'rgba(148, 163, 184, 0.15)' : 'rgba(244, 63, 94, 0.4)'}`,
              borderRadius: 'var(--radius-md)',
              padding: '0.75rem',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              position: 'relative',
              overflow: 'hidden',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
              <span style={{ fontSize: '1.2rem' }}>{c.icon}</span>
              {c.nominal ? (
                <CheckCircle2 size={13} color="#10b981" />
              ) : (
                <AlertCircle size={13} color="#f43f5e" />
              )}
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#f8fafc' }}>{c.name}</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: c.nominal ? '#38bdf8' : '#fb7185', fontWeight: 600, marginTop: '0.15rem' }}>
                {c.value}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* What-If Simulator Section */}
      <div style={{
        background: 'rgba(15, 23, 42, 0.6)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-md)',
        padding: '0.85rem 1rem',
        marginTop: 'auto',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.65rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.78rem', fontWeight: 600, color: '#e2e8f0' }}>
            <Sliders size={14} color="#f59e0b" />
            <span>Scenario Stress Test (What-If)</span>
          </div>
          <button
            onClick={() => { setWhatIfTempOffset(0); setWhatIfPressureDrop(0); }}
            style={{ background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', fontSize: '0.72rem', display: 'flex', alignItems: 'center', gap: '0.2rem' }}
          >
            <RefreshCw size={10} /> Reset
          </button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 100px', gap: '1rem', alignItems: 'center' }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '0.2rem' }}>
              <span>Oil Temp Offset</span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>+{whatIfTempOffset}°C</span>
            </div>
            <input
              type="range"
              min="0"
              max="25"
              step="1"
              value={whatIfTempOffset}
              onChange={(e) => setWhatIfTempOffset(Number(e.target.value))}
              style={{ width: '100%', accentColor: '#ec4899', cursor: 'pointer' }}
            />
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '0.2rem' }}>
              <span>Air Leak Pressure Drop</span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>-{whatIfPressureDrop} bar</span>
            </div>
            <input
              type="range"
              min="0"
              max="3"
              step="0.2"
              value={whatIfPressureDrop}
              onChange={(e) => setWhatIfPressureDrop(Number(e.target.value))}
              style={{ width: '100%', accentColor: '#06b6d4', cursor: 'pointer' }}
            />
          </div>

          <div style={{ textAlign: 'right', borderLeft: '1px solid var(--border-subtle)', paddingLeft: '0.75rem' }}>
            <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)' }}>Simulated Health</div>
            <div style={{
              fontFamily: 'var(--font-heading)',
              fontSize: '1.25rem',
              fontWeight: 700,
              color: simHealth > 75 ? '#10b981' : simHealth > 50 ? '#f59e0b' : '#f43f5e'
            }}>
              {simHealth}%
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
