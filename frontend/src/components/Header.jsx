import React from 'react';
import { Activity, RefreshCw, Radio, Server, Database, Clock, Sun, Moon, Palette } from 'lucide-react';

export default function Header({
  health,
  latestTime,
  isRefreshing,
  refreshInterval,
  setRefreshInterval,
  onManualRefresh,
  timeRange,
  setTimeRange,
  theme,
  setTheme,
}) {
  const isHealthy = health?.status === 'ok';

  const toggleTheme = () => {
    // Cycle through hybrid -> light -> dark -> hybrid
    const nextTheme = theme === 'hybrid' ? 'light' : theme === 'light' ? 'dark' : 'hybrid';
    setTheme(nextTheme);
    document.documentElement.setAttribute('data-theme', nextTheme);
  };

  return (
    <header className="glass-panel" style={{ padding: '1.25rem 1.75rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        {/* Title and Branding */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{
            width: '46px',
            height: '46px',
            borderRadius: '12px',
            background: 'linear-gradient(135deg, #0284c7 0%, #2563eb 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 14px rgba(37, 99, 235, 0.3)',
          }}>
            <Activity size={24} color="#ffffff" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <h1 style={{
                fontFamily: 'var(--font-heading)',
                fontSize: '1.5rem',
                fontWeight: 700,
                letterSpacing: '-0.02em',
                color: 'var(--text-main)',
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
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem', flexWrap: 'wrap' }}>
          {/* Latest Data Anchor Time */}
          {latestTime && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.45rem',
              padding: '0.45rem 0.85rem',
              background: 'var(--bg-secondary)',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-subtle)',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.78rem',
              color: 'var(--text-muted)'
            }}>
              <Clock size={14} color="var(--accent-cyan)" />
              <span>Data Time: <strong style={{ color: 'var(--text-main)' }}>{new Date(latestTime).toUTCString().slice(5, 22)}</strong></span>
            </div>
          )}

          {/* Time Range Selector */}
          <div style={{ display: 'flex', background: 'var(--bg-secondary)', padding: '3px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            {[1, 6, 12, 24].map((h) => (
              <button
                key={h}
                className={`btn-control ${timeRange === h ? 'active' : ''}`}
                style={{ padding: '0.35rem 0.75rem', fontSize: '0.8rem', border: 'none', boxShadow: 'none' }}
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
                background: 'var(--bg-secondary)',
                color: 'var(--text-main)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '0.45rem 0.75rem',
                fontSize: '0.8rem',
                outline: 'none',
                cursor: 'pointer',
                boxShadow: 'var(--shadow-sm)'
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
            <RefreshCw size={15} style={{ animation: isRefreshing ? 'spin 1s linear infinite' : 'none' }} />
            <span>Sync</span>
          </button>

          {/* Theme Switcher Button */}
          <button
            className="btn-control"
            onClick={toggleTheme}
            title={`Current Theme: ${theme.toUpperCase()} (Click to toggle)`}
            style={{ padding: '0.45rem 0.75rem', fontSize: '0.78rem', textTransform: 'capitalize' }}
          >
            <Palette size={15} color="var(--accent-cyan)" />
            <span>{theme}</span>
          </button>
        </div>
      </div>
      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </header>
  );
}
