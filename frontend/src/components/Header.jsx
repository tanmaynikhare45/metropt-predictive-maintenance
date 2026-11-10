import { useState } from 'react'
import { computeStatus } from '../utils/status'
import { fmtFull, toMs } from '../utils/time'

export default function Header({ apiOk, latest, failures, live, pinnedEnd, onLive, onPin, simulation, simulationStarting, simulationStatus, onSimulate, onStopSimulation }) {
  const [activeFailure, setActiveFailure] = useState(null)
  const [simulationError, setSimulationError] = useState('')
  const status = computeStatus(latest, apiOk)
  const dataTime = latest?.sensors?.time
  const replayActive = ['running', 'draining'].includes(simulationStatus?.status)

  const [customStart, setCustomStart] = useState(() => {
    return '2020-04-17T18:00'
  })
  const [customDuration, setCustomDuration] = useState(24)
  const [customSpeed, setCustomSpeed] = useState(300)

  const pinDefault = () => dataTime || failures?.[0]?.start_time || null

  const handleSelectFailure = (f) => {
    setActiveFailure(f)
    onPin(f.start_time)
  }

  const handleLive = () => {
    setActiveFailure(null)
    onLive()
  }

  const handleStartCustomSimulation = async () => {
    if (!customStart) return
    setSimulationError('')
    const startStr = customStart.includes('T') ? customStart : customStart.replace(' ', 'T')
    const startDate = new Date(startStr.length === 16 ? `${startStr}:00Z` : `${startStr}Z`)
    const endDate = new Date(startDate.getTime() + customDuration * 3600 * 1000)
    try {
      await onSimulate({
        start_time: startDate.toISOString(),
        end_time: endDate.toISOString(),
        speed: customSpeed,
      })
    } catch (e) {
      setSimulationError(e?.response?.data?.detail || e.message || 'Could not start simulation')
    }
  }

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
          <button className={live ? 'on' : ''} onClick={handleLive}>Live</button>
          <button className={!live ? 'on' : ''} disabled={!pinDefault()} onClick={() => !pinnedEnd && onPin(pinDefault())}>
            Pinned
          </button>
        </div>
        {live && (
          <div className="live-sim-bar" role="group" aria-label="Live simulation controls">
            <span className="muted">Simulate from (UTC)</span>
            <input
              type="datetime-local"
              value={customStart}
              onChange={(e) => setCustomStart(e.target.value)}
              disabled={!!simulation || simulationStarting || replayActive}
              title="Select starting date and time for live simulation"
            />
            <select
              value={customDuration}
              onChange={(e) => setCustomDuration(Number(e.target.value))}
              disabled={!!simulation || simulationStarting || replayActive}
              className="sim-select"
              title="Simulation window duration"
            >
              <option value={6}>6 hours</option>
              <option value={12}>12 hours</option>
              <option value={24}>24 hours</option>
              <option value={48}>48 hours</option>
              <option value={72}>3 days</option>
            </select>
            <select
              value={customSpeed}
              onChange={(e) => setCustomSpeed(Number(e.target.value))}
              disabled={!!simulation || simulationStarting || replayActive}
              className="sim-select"
              title="Simulation replay speed"
            >
              <option value={100}>100×</option>
              <option value={200}>200×</option>
              <option value={300}>300×</option>
              <option value={500}>500×</option>
            </select>
            {!simulation && !replayActive ? (
              <button
                className="chip on"
                disabled={!apiOk || simulationStarting || !customStart}
                onClick={handleStartCustomSimulation}
                title="Start live simulation from selected date and time"
              >
                {simulationStarting ? 'Starting…' : '▶ Start Simulation'}
              </button>
            ) : (
              <button
                className="chip stop-btn"
                onClick={onStopSimulation}
                title="Stop live simulation"
              >
                ⏹ Stop Simulation
              </button>
            )}
          </div>
        )}
        {!live && pinnedEnd && (
          <label className="pin-input">
            <span className="muted">Pinned to (UTC)</span>
            <input
              type="datetime-local"
              value={pinnedEnd.replace(' ', 'T').slice(0, 16)}
              onChange={(e) => e.target.value && onPin(`${e.target.value}:00Z`)}
            />
          </label>
        )}
        <div className="shortcuts">
          <span className="muted">Failure events</span>
          {(failures || []).map((f, i) => (
            <span className="failure-actions" key={f.id ?? i}>
              <button
                className={`chip ${!live && activeFailure?.id === f.id ? 'on' : ''}`}
                onClick={() => handleSelectFailure(f)}
              >Failure {i + 1}</button>
              <button className="chip" disabled={!apiOk || !!simulation || simulationStarting || replayActive} title="Replay this failure through the model and alert pipeline" onClick={async () => {
                setSimulationError('')
                try { await onSimulate(f) } catch (e) { setSimulationError(e?.response?.data?.detail || e.message || 'Could not start simulation') }
              }}>{simulationStarting ? 'Starting…' : 'Simulate'}</button>
            </span>
          ))}
        </div>
      </div>
      {simulation && (
        <div className="simulation-bar" role="status">
          <span>{simulation.failed ? (simulationStatus?.status === 'incomplete' ? 'Replay ended before the interval was fully stored' : 'Replay process failed') : simulation.playing ? (simulationStatus?.status === 'draining' ? 'Waiting for the consumer to write replayed readings' : 'Replaying historical data') : 'Replay complete'} · {SIMULATION_SPEED_LABEL} · {fmtFull(simulation.currentMs)}<small>Progress: {Math.floor(simulationStatus?.progress || 0)}% · Publisher: {simulationStatus?.publisher || 'starting'} · Consumer: {simulationStatus?.consumer || 'starting'} · Slack needs SLACK_WEBHOOK_URL in .env.</small></span>
          <button className="chip" onClick={onStopSimulation}>Stop</button>
        </div>
      )}
      {simulationStarting && <div className="simulation-bar" role="status">Preparing the isolated replay stream and consumer. The dashboard will follow stored sensor data as soon as it arrives.</div>}
      {simulationError && <div className="simulation-error" role="alert">Simulation could not start: {simulationError}</div>}
    </header>
  )
}

const SIMULATION_SPEED_LABEL = '300× data time'
