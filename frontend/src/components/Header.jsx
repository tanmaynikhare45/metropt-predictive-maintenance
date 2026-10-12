import React from 'react';
import { Activity, RefreshCw, Radio, Server, Database, Clock } from 'lucide-react';

export default function Header({
  health,
  latestTime,
  isRefreshing,
  refreshInterval,
  setRefreshInterval,
  onManualRefresh,
  timeRange,
  setTimeRange,
}) {
  const isHealthy = health?.status === 'ok';

  return (
    <header className="glass-panel" style={{ padding: '1.25rem 1.75rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        {/* Title and Branding */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{
            width: '46px',
            height: '46px',
            borderRadius: '12px',
            background: 'linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 16px rgba(6, 182, 212, 0.4)',
          }}>
            <Activity size={26} color="#ffffff" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <h1 style={{
                fontFamily: 'var(--font-heading)',
                fontSize: '1.5rem',
                fontWeight: 700,
                letterSpacing: '-0.02em',
                background: 'linear-gradient(90deg, #ffffff 0%, #cbd5e1 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}>
                MetroPT-3 APU Predictive Maintenance
              </h1>
              <span className={`status-badge ${isHealthy ? 'nominal' : 'critical'}`}>
                <span className={`pulse-dot ${isHealthy ? 'green' : 'red'}`} />
                {isHealthy ? 'LIVE PIPELINE' : 'BACKEND OFFLINE'}
              </span>
            </div>
            <p style={{ fontSize: '0.825rem', color: 'var(--text-muted)', marginTop: '0.15rem' }}>
              Air Production Unit Telemetry • Streaming Ingestion & Real-Time ML Inference
            </p>
          </div>
        </div>

        {/* Global Controls & Status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
          {/* Latest Data Anchor Time */}
          {latestTime && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.45rem',
              padding: '0.4rem 0.8rem',
              background: 'rgba(30, 41, 59, 0.5)',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-subtle)',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.78rem',
              color: 'var(--text-muted)'
            }}>
              <Clock size={14} color="#38bdf8" />
              <span>Data Time: <strong style={{ color: '#f8fafc' }}>{new Date(latestTime).toUTCString().slice(5, 22)}</strong></span>
            </div>
          )}

          {/* Time Range Selector */}
          <div style={{ display: 'flex', background: 'rgba(30, 41, 59, 0.6)', padding: '3px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            {[1, 6, 12, 24].map((h) => (
              <button
                key={h}
                className={`btn-control ${timeRange === h ? 'active' : ''}`}
                style={{ padding: '0.35rem 0.75rem', fontSize: '0.8rem' }}
                onClick={() => setTimeRange(h)}
              >
                {h}h
              </button>
            ))}
          </div>

          {/* Polling Interval Select */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-dim)' }}>Refresh:</span>
            <select
              value={refreshInterval}
              onChange={(e) => setRefreshInterval(Number(e.target.value))}
              style={{
                background: 'rgba(30, 41, 59, 0.8)',
                color: 'var(--text-main)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '0.4rem 0.65rem',
                fontSize: '0.8rem',
                outline: 'none',
                cursor: 'pointer',
              }}
            >
              <option value={0}>Paused</option>
              <option value={3000}>3s (Live)</option>
              <option value={5000}>5s</option>
              <option value={10000}>10s</option>
            </select>
          </div>

          {/* Manual Refresh Button */}
          <button
            className="btn-control"
            onClick={onManualRefresh}
            title="Refresh Now"
            disabled={isRefreshing}
          >
            <RefreshCw size={15} className={isRefreshing ? 'spin' : ''} style={{ animation: isRefreshing ? 'spin 1s linear infinite' : 'none' }} />
            <span>Sync</span>
          </button>
        </div>
      </div>
      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </header>
  );
}
