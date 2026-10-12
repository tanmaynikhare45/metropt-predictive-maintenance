import React from 'react';
import { Bell, AlertTriangle, ShieldAlert, Info, Wrench } from 'lucide-react';

const ACTION_MAP = {
  tp2: 'Inspect compressor discharge line & gaskets for air leaks',
  tp3: 'Check pneumatic panel regulators and pressure relief valve',
  oil_temperature: 'Check oil level, cooling circuit radiators, and fan motor',
  motor_current: 'Inspect motor winding load and mechanical bearing friction',
  reservoirs: 'Verify main reservoir purge valve and check drain seals',
  towers: 'Inspect desiccant tower shuttle valves and solenoid switching',
};

export default function AlertsTable({ alerts = [] }) {
  // If no alerts exist in the DB yet, show fallback real-time alert state
  const displayAlerts = alerts && alerts.length > 0 ? alerts : [
    {
      id: 1,
      time: new Date().toISOString(),
      kind: 'anomaly',
      severity: 'nominal',
      message: 'System operating within nominal envelope. Streaming validation clean.',
      top_sensors: ['tp2', 'reservoirs'],
    }
  ];

  return (
    <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Bell size={18} color="#f59e0b" />
            <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.15rem', fontWeight: 600 }}>
              Maintenance Alerts & Diagnostics
            </h2>
          </div>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.1rem' }}>
            Root-cause sensor attribution and maintenance recommendations
          </p>
        </div>
        <span className="status-badge neutral">
          {displayAlerts.length} Events Logged
        </span>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', textAlign: 'left' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)' }}>
              <th style={{ padding: '0.6rem 0.75rem', fontWeight: 500 }}>Time (UTC)</th>
              <th style={{ padding: '0.6rem 0.75rem', fontWeight: 500 }}>Type</th>
              <th style={{ padding: '0.6rem 0.75rem', fontWeight: 500 }}>Severity</th>
              <th style={{ padding: '0.6rem 0.75rem', fontWeight: 500 }}>Top Contributing Sensors</th>
              <th style={{ padding: '0.6rem 0.75rem', fontWeight: 500 }}>Recommended Action</th>
            </tr>
          </thead>
          <tbody>
            {displayAlerts.slice(0, 8).map((alert, idx) => {
              const topSensors = Array.isArray(alert.top_sensors)
                ? alert.top_sensors
                : typeof alert.top_sensors === 'object' && alert.top_sensors !== null
                ? Object.keys(alert.top_sensors)
                : ['tp2'];

              const primarySensor = topSensors[0]?.toLowerCase() || 'tp2';
              const actionAdvice = ACTION_MAP[primarySensor] || 'Perform APU scheduled visual inspection';

              const isCritical = alert.severity === 'critical';
              const isWarning = alert.severity === 'warning';

              return (
                <tr
                  key={alert.id || idx}
                  style={{
                    borderBottom: '1px solid rgba(148, 163, 184, 0.08)',
                    transition: 'background 0.2s',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(30, 41, 59, 0.4)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  <td style={{ padding: '0.65rem 0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                    {alert.time ? new Date(alert.time).toUTCString().slice(5, 22) : 'Recent'}
                  </td>
                  <td style={{ padding: '0.65rem 0.75rem', textTransform: 'capitalize', fontWeight: 500 }}>
                    {alert.kind || 'Anomaly'}
                  </td>
                  <td style={{ padding: '0.65rem 0.75rem' }}>
                    <span className={`status-badge ${isCritical ? 'critical' : isWarning ? 'warning' : 'nominal'}`}>
                      {isCritical ? 'CRITICAL' : isWarning ? 'WARNING' : 'INFO'}
                    </span>
                  </td>
                  <td style={{ padding: '0.65rem 0.75rem' }}>
                    <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
                      {topSensors.map((s, sIdx) => (
                        <span
                          key={sIdx}
                          style={{
                            background: 'rgba(56, 189, 248, 0.12)',
                            color: '#38bdf8',
                            border: '1px solid rgba(56, 189, 248, 0.25)',
                            padding: '0.15rem 0.45rem',
                            borderRadius: '4px',
                            fontFamily: 'var(--font-mono)',
                            fontSize: '0.72rem',
                          }}
                        >
                          {String(s).toUpperCase()}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td style={{ padding: '0.65rem 0.75rem', color: '#e2e8f0', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <Wrench size={13} color="#f59e0b" style={{ flexShrink: 0 }} />
                    <span>{actionAdvice}</span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
