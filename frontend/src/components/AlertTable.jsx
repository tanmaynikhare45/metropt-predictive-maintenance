import { getAlerts } from '../api'
import usePolling from '../hooks/usePolling'
import { topSensorsText } from '../utils/format'
import { fmtFull, toMs } from '../utils/time'
import Card from './Card'

export default function AlertTable({ refreshMs, className }) {
  const { data, error, loading } = usePolling(() => getAlerts(20), [], refreshMs)
  const rows = data || []

  return (
    <Card
      className={className}
      title="Alert history"
      subtitle="Newest first"
      loading={loading && !data}
      error={error}
      empty={!loading && rows.length === 0}
      emptyText="No alerts yet. Alerts are created by the alert service in Phase 6."
    >
      <div className="table-wrap">
        <table>
          <thead>
            <tr><th>Time (UTC)</th><th>Severity</th><th>Type</th><th>Message</th><th>Top sensors</th></tr>
          </thead>
          <tbody>
            {rows.map((a) => (
              <tr key={a.id}>
                <td>{fmtFull(toMs(a.time))}</td>
                <td><span className={`tag sev-${a.severity}`}>{a.severity}</span></td>
                <td>{a.kind}</td>
                <td>{a.message || '–'}</td>
                <td>{topSensorsText(a.top_sensors)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  )
}
