import { getAlerts } from '../api'
import usePolling from '../hooks/usePolling'
import { parseSlackMessage, parseTopSensors, topSensorsText } from '../utils/format'
import { fmtFull, toMs } from '../utils/time'
import Card from './Card'

export default function AlertTable({ refreshMs, className, onPin, pinnedEnd }) {
  const { data, error, loading } = usePolling(() => getAlerts(20), [], refreshMs)
  const rows = data || []
  const pinnedMs = pinnedEnd ? toMs(pinnedEnd) : null

  return (
    <Card
      className={className}
      title="Alert history"
      subtitle={onPin ? 'Newest first · click a row or pin button to view dashboard at that alert time' : 'Newest first'}
      loading={loading && !data}
      error={error}
      empty={!loading && rows.length === 0}
      emptyText="No alerts yet. Alerts are created by the alert service in Phase 6."
    >
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th className="col-time">Time (UTC)</th>
              <th className="col-sev">Severity</th>
              <th className="col-type">Type</th>
              <th className="col-msg">Diagnosis & Action</th>
              <th className="col-sensors">Top sensors</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((a) => {
              const aMs = toMs(a.time)
              const isPinned = pinnedMs != null && aMs === pinnedMs
              const parsed = parseSlackMessage(a.message, a.severity)
              const sensors = parseTopSensors(a.top_sensors)

              return (
                <tr
                  key={a.id}
                  className={`alert-row ${isPinned ? 'row-pinned' : ''}`}
                  onClick={() => onPin && onPin(a.time)}
                  style={{ cursor: onPin ? 'pointer' : 'default' }}
                  title={onPin ? 'Click to pin dashboard to this alert time' : undefined}
                >
                  <td className="time-col">
                    <div>{fmtFull(aMs)}</div>
                    {isPinned && <span className="pinned-indicator">📍 PINNED</span>}
                  </td>
                  <td className="sev-col">
                    <span className={`tag sev-${a.severity}`}>{a.severity}</span>
                  </td>
                  <td className="type-col">
                    <span className="kind-badge">{a.kind}</span>
                  </td>
                  <td className="msg-col">
                    {parsed ? (
                      <div className="alert-cell">
                        <div className="alert-cell-header">
                          <span className="alert-emoji">{parsed.emoji}</span>
                          <strong className="alert-title">{parsed.title}</strong>
                          {onPin && (
                            <button
                              type="button"
                              className="alert-pin-btn"
                              onClick={(e) => {
                                e.stopPropagation()
                                onPin(a.time)
                              }}
                              title="Pin dashboard to this alert time"
                            >
                              {isPinned ? '✓ Pinned' : 'Pin to time'}
                            </button>
                          )}
                        </div>

                        {parsed.incident && (
                          <div className="alert-cell-meta">
                            <span className="alert-meta-label">Incident:</span>
                            {parsed.incident}
                          </div>
                        )}

                        {parsed.ongoing && (
                          <div className="alert-cell-meta">
                            <span className="alert-meta-label">Ongoing:</span>
                            {parsed.ongoing}
                          </div>
                        )}

                        {parsed.scores.length > 0 && (
                          <div className="alert-cell-scores">
                            {parsed.scores.map((sc, i) => (
                              <span key={i}>{sc}</span>
                            ))}
                          </div>
                        )}

                        {parsed.causes && (
                          <div className="alert-cell-cause">
                            <span className="alert-cause-label">Likely cause:</span>
                            {parsed.causes}
                          </div>
                        )}

                        {parsed.action && (
                          <div className="alert-cell-action">
                            <span className="alert-action-badge">Action</span>
                            <span className="alert-action-text">{parsed.action}</span>
                          </div>
                        )}

                        {parsed.otherLines.length > 0 && (
                          <div className="alert-cell-meta">
                            {parsed.otherLines.join(' · ')}
                          </div>
                        )}
                      </div>
                    ) : (
                      <span>{a.message || '–'}</span>
                    )}
                  </td>
                  <td className="sensors-col">
                    {sensors.length > 0 ? (
                      <div className="sensor-chips">
                        {sensors.map((s, idx) => (
                          <span key={idx} className="sensor-chip">
                            <strong>{s.name}</strong>
                            {s.val != null && `: ${s.val}`}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="muted">{topSensorsText(a.top_sensors)}</span>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </Card>
  )
}
