import React from 'react';
import { ShieldCheck, AlertTriangle, Cpu, Gauge, Zap, Flame, Wind } from 'lucide-react';

export default function SystemOverviewCards({ latestData, predictionsData }) {
  const sensors = latestData?.sensors || {};
  const preds = latestData?.predictions || {};

  // Extract ML metrics
  const failureRisk = preds?.failure_risk?.score !== undefined ? preds.failure_risk.score : 0.05;
  const ifScore = preds?.iforest?.score !== undefined ? preds.iforest.score : 0.12;
  const isAnomaly = preds?.iforest?.flag || preds?.failure_risk?.flag || false;

  // Calculate Health Index (0 - 100)
  // Health diminishes with higher anomaly score and failure risk
  const healthIndex = Math.max(0, Math.min(100, Math.round(100 * (1 - 0.45 * Math.min(1, ifScore * 2) - 0.55 * failureRisk))));

  // Determine severity tier
  let healthTier = { text: 'Nominal Condition', badge: 'nominal', dot: 'green', color: '#10b981' };
  if (healthIndex < 50 || failureRisk > 0.6) {
    healthTier = { text: 'Critical Attention', badge: 'critical', dot: 'red', color: '#f43f5e' };
  } else if (healthIndex < 80 || failureRisk > 0.3) {
    healthTier = { text: 'Degraded / Watch', badge: 'warning', dot: 'amber', color: '#f59e0b' };
  }

  // Determine compressor cycling state (COMP digital signal: 1 = Loaded/Pumping, 0 = Idling)
  const isCompressorLoaded = (sensors.comp || 0) > 0.5 || (sensors.motor_current || 0) > 4.0;

  return (
    <div className="grid-cards">
      {/* 1. Health Index Card */}
      <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              APU Health Index
            </span>
            <div style={{ display: 'flex', alignItems: 'baseline', marginTop: '0.35rem' }}>
              <span className="metric-value" style={{ color: healthTier.color }}>
                {healthIndex}
              </span>
              <span className="metric-unit">/ 100</span>
            </div>
          </div>
          <div style={{
            width: '42px',
            height: '42px',
            borderRadius: '10px',
            background: `${healthTier.color}20`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: `1px solid ${healthTier.color}40`,
          }}>
            <ShieldCheck size={22} color={healthTier.color} />
          </div>
        </div>

        <div style={{ marginTop: '1.2rem' }}>
          <div style={{
            width: '100%',
            height: '6px',
            background: 'rgba(51, 65, 85, 0.5)',
            borderRadius: '99px',
            overflow: 'hidden',
            marginBottom: '0.75rem',
          }}>
            <div style={{
              width: `${healthIndex}%`,
              height: '100%',
              background: `linear-gradient(90deg, ${healthTier.color}aa, ${healthTier.color})`,
              borderRadius: '99px',
              transition: 'width 0.5s ease',
            }} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className={`status-badge ${healthTier.badge}`}>
              <span className={`pulse-dot ${healthTier.dot}`} />
              {healthTier.text}
            </span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
              RUL: {healthIndex > 70 ? '> 72h' : healthIndex > 50 ? '12 - 24h' : '< 6h'}
            </span>
          </div>
        </div>
      </div>

      {/* 2. Failure Risk Card */}
      <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Air-Leak Failure Risk (6h)
            </span>
            <div style={{ display: 'flex', alignItems: 'baseline', marginTop: '0.35rem' }}>
              <span className="metric-value" style={{ color: failureRisk > 0.5 ? '#f43f5e' : failureRisk > 0.25 ? '#f59e0b' : '#38bdf8' }}>
                {(failureRisk * 100).toFixed(1)}%
              </span>
            </div>
          </div>
          <div style={{
            width: '42px',
            height: '42px',
            borderRadius: '10px',
            background: failureRisk > 0.5 ? 'rgba(244, 63, 94, 0.15)' : 'rgba(56, 189, 248, 0.15)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: `1px solid ${failureRisk > 0.5 ? 'rgba(244, 63, 94, 0.3)' : 'rgba(56, 189, 248, 0.3)'}`,
          }}>
            <AlertTriangle size={22} color={failureRisk > 0.5 ? '#fb7185' : '#38bdf8'} />
          </div>
        </div>

        <div style={{ marginTop: '1.2rem' }}>
          <div style={{
            width: '100%',
            height: '6px',
            background: 'rgba(51, 65, 85, 0.5)',
            borderRadius: '99px',
            overflow: 'hidden',
            marginBottom: '0.75rem',
          }}>
            <div style={{
              width: `${Math.min(100, Math.max(2, failureRisk * 100))}%`,
              height: '100%',
              background: failureRisk > 0.5 ? 'linear-gradient(90deg, #f59e0b, #ef4444)' : 'linear-gradient(90deg, #06b6d4, #3b82f6)',
              borderRadius: '99px',
              transition: 'width 0.5s ease',
            }} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Model: Random Forest / XGB
            </span>
            <span className={`status-badge ${failureRisk > 0.5 ? 'critical' : failureRisk > 0.25 ? 'warning' : 'nominal'}`}>
              {failureRisk > 0.5 ? 'HIGH RISK' : failureRisk > 0.25 ? 'ELEVATED' : 'LOW RISK'}
            </span>
          </div>
        </div>
      </div>

      {/* 3. Anomaly Detector Card */}
      <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Anomaly Score (Isolation Forest)
            </span>
            <div style={{ display: 'flex', alignItems: 'baseline', marginTop: '0.35rem' }}>
              <span className="metric-value" style={{ color: isAnomaly ? '#f43f5e' : '#a855f7' }}>
                {ifScore.toFixed(3)}
              </span>
              <span className="metric-unit">thresh: 0.50</span>
            </div>
          </div>
          <div style={{
            width: '42px',
            height: '42px',
            borderRadius: '10px',
            background: 'rgba(168, 85, 247, 0.15)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: '1px solid rgba(168, 85, 247, 0.3)',
          }}>
            <Cpu size={22} color="#c084fc" />
          </div>
        </div>

        <div style={{ marginTop: '1.2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
            Unsupervised 36-feature vector
          </div>
          <span className={`status-badge ${isAnomaly ? 'critical' : 'nominal'}`}>
            <span className={`pulse-dot ${isAnomaly ? 'red' : 'green'}`} />
            {isAnomaly ? 'ANOMALY DETECTED' : 'NORMAL PATTERN'}
          </span>
        </div>
      </div>

      {/* 4. Compressor Load & Telemetry Card */}
      <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              APU Operational State
            </span>
            <div style={{ display: 'flex', alignItems: 'baseline', marginTop: '0.35rem' }}>
              <span className="metric-value" style={{ color: isCompressorLoaded ? '#38bdf8' : '#94a3b8', fontSize: '1.8rem' }}>
                {isCompressorLoaded ? 'LOADED' : 'IDLING'}
              </span>
            </div>
          </div>
          <div style={{
            width: '42px',
            height: '42px',
            borderRadius: '10px',
            background: 'rgba(6, 182, 212, 0.15)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: '1px solid rgba(6, 182, 212, 0.3)',
          }}>
            <Gauge size={22} color="#22d3ee" />
          </div>
        </div>

        <div style={{ marginTop: '1rem', display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.5rem', borderTop: '1px solid var(--border-subtle)', paddingTop: '0.75rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: 'var(--text-dim)', fontSize: '0.7rem' }}>
              <Zap size={11} color="#f59e0b" /> Motor
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', fontWeight: 600, color: '#f8fafc' }}>
              {(sensors.motor_current || 0).toFixed(1)} A
            </div>
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: 'var(--text-dim)', fontSize: '0.7rem' }}>
              <Flame size={11} color="#f43f5e" /> Oil Temp
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', fontWeight: 600, color: '#f8fafc' }}>
              {(sensors.oil_temperature || 0).toFixed(1)} °C
            </div>
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: 'var(--text-dim)', fontSize: '0.7rem' }}>
              <Wind size={11} color="#06b6d4" /> Pressure
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', fontWeight: 600, color: '#f8fafc' }}>
              {(sensors.reservoirs || 0).toFixed(2)} bar
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
