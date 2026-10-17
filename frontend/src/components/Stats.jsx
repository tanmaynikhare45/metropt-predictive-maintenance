import { fmtFull, fmtNum, toMs } from '../utils/time'

function Row({ label, value, hint }) {
  return (
    <div className="stat">
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
      {hint && <span className="stat-hint">{hint}</span>}
    </div>
  )
}

export default function Stats({ latest, config }) {
  const p = latest?.predictions || {}
  const win = p.failure_risk?.time || p.iforest?.time
  return (
    <div className="stats">
      <Row label="Isolation Forest score" value={fmtNum(p.iforest?.score)} hint={config?.iforest_threshold != null ? `threshold ${fmtNum(config.iforest_threshold)}` : null} />
      {p.lstm_ae && <Row label="LSTM autoencoder error" value={fmtNum(p.lstm_ae.score, 4)} hint={config?.lstm_threshold != null ? `threshold ${fmtNum(config.lstm_threshold, 4)}` : null} />}
      <Row label="Failure risk score" value={fmtNum(p.failure_risk?.score)} hint={config?.failure_threshold != null ? `threshold ${fmtNum(config.failure_threshold)}` : null} />
      <Row label="Newest scored window" value={win ? fmtFull(toMs(win)) : '–'} />
    </div>
  )
}
