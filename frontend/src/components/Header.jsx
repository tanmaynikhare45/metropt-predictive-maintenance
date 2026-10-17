import { useState } from 'react'
import { computeStatus } from '../utils/status'
import { fmtFull, shiftIso, toMs } from '../utils/time'

const PIN_HOURS_BEFORE = 3
// where a "Failure N" button jumps to, relative to the failure's start
const JUMPS = [
  { hours: -PIN_HOURS_BEFORE, label: '3 h before' },
  { hours: 0, label: 'at start' },
  { hours: 6, label: '6 h after' },
]

export default function Header({ apiOk, latest, failures, live, pinnedEnd, onLive, onPin }) {
  const [jump, setJump] = useState(JUMPS[0].hours)
  const status = computeStatus(latest, apiOk)
  const dataTime = latest?.sensors?.time

  const pinDefault = () => dataTime || (failures?.[0] ? shiftIso(failures[0].start_time, -PIN_HOURS_BEFORE) : null)

  return (
    <header className="topbar">
      <div className="brand">
        <span className="logo" aria-hidden="true">🚆</span>
        <div>
          <h1>Metro compressor (APU): predictive maintenance</h1>
          <p className="muted">MetroPT-3 dataset · all times UTC</p>
        </div>
      </div>

      <div className="topbar-right">
        <div className={`badge lvl-${status.level}`} title="Overall status from the newest scores">
          <span className="dot" />
          {status.label}
        </div>
        <div className="clock">
          <span className="muted">{live ? 'Newest data' : 'Data up to'}</span>
          <strong>{dataTime ? fmtFull(toMs(dataTime)) : '–'}</strong>
        </div>
      </div>

      <div className="timebar">
        <div className="seg" role="group" aria-label="Time mode">
          <button className={live ? 'on' : ''} onClick={onLive}>Live</button>
          <button className={!live ? 'on' : ''} disabled={!pinDefault()} onClick={() => !pinnedEnd && onPin(pinDefault())}>
            Pinned
          </button>
        </div>
        {!live && pinnedEnd && (
          <label className="pin-input">
            <span className="muted">Pinned to (UTC)</span>
            <input
              type="datetime-local"
              value={pinnedEnd.slice(0, 16)}
              onChange={(e) => e.target.value && onPin(`${e.target.value}:00Z`)}
            />
          </label>
        )}
        <div className="shortcuts">
          <span className="muted">Jump to</span>
          {(failures || []).map((f, i) => (
            <button key={f.id ?? i} className="chip" onClick={() => onPin(shiftIso(f.start_time, jump))}>
              Failure {i + 1}
            </button>
          ))}
          <div className="seg" role="group" aria-label="Jump offset">
            {JUMPS.map((j) => (
              <button key={j.hours} className={j.hours === jump ? 'on' : ''} onClick={() => setJump(j.hours)}>{j.label}</button>
            ))}
          </div>
        </div>
      </div>
    </header>
  )
}
