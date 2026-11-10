import { useEffect, useState } from 'react'
import { API_URL, getConfig, getFailures, getHealth, getLatest, getSimulationStatus, startSimulation, stopSimulation } from './api'
import AlertTable from './components/AlertTable'
import AnomalyChart from './components/AnomalyChart'
import Card from './components/Card'
import ForecastChart from './components/ForecastChart'
import Header from './components/Header'
import RiskGauge from './components/RiskGauge'
import SensorChart from './components/SensorChart'
import Stats from './components/Stats'
import TwinPlaceholder from './components/TwinPlaceholder'
import usePolling from './hooks/usePolling'

const SIM_SPEED = 300 // 300x data time; the display clock follows persisted sensor readings

function getUrlEnd() {
  const params = new URLSearchParams(window.location.search)
  const val = params.get('end')
  return val ? val.trim() : null
}

export default function App() {
  // Live: no `end`, the API anchors at the newest reading. Pinned: every request gets end=<time>.
  // Check URL query param (e.g. from Slack alert links: /?end=2020-06-05T06:50:00Z)
  const [pinnedEnd, setPinnedEndState] = useState(getUrlEnd)
  const [simulation, setSimulation] = useState(null)
  const [simulationStarting, setSimulationStarting] = useState(false)
  const end = simulation ? new Date(simulation.currentMs).toISOString() : (pinnedEnd || undefined)
  const live = !simulation && !pinnedEnd

  const setPinnedEnd = (val) => {
    if (simulation) stopSimulation().catch(() => {})
    setSimulation(null)
    setPinnedEndState(val)
    const url = new URL(window.location)
    if (val) {
      url.searchParams.set('end', val)
    } else {
      url.searchParams.delete('end')
    }
    window.history.replaceState({}, '', url)
  }

  const beginSimulation = async (failure) => {
    const start = new Date(failure.start_time).toISOString()
    const finish = new Date(failure.end_time).toISOString()
    const speed = failure.speed || SIM_SPEED
    const isCustom = !failure.id
    const promptText = isCustom
      ? `Start live simulation replay from ${start} to ${finish} (speed ${speed}×)? This will stream sensor readings through Kafka and update the dashboard in real time.`
      : `Replay the known failure interval ${start} to ${finish}? This will remove sensor readings, predictions, and alert history in that interval from the database, then rebuild them from the original parquet file. If replay is stopped early, the interval will be only partly restored.`
    const confirmed = window.confirm(promptText)
    if (!confirmed) return
    setSimulationStarting(true)
    try {
      const started = await startSimulation({ start, end: finish, speed, reset_interval: true })
      const resumedStart = started.start || start
      const resumedEnd = started.end || finish
      setPinnedEndState(null)
      const url = new URL(window.location)
      url.searchParams.delete('end')
      window.history.replaceState({}, '', url)
      setSimulation({ startMs: Date.parse(resumedStart), endMs: Date.parse(resumedEnd), currentMs: Date.parse(started.sensor_time || resumedStart), speed: started.speed || speed, playing: true })
    } finally {
      setSimulationStarting(false)
    }
  }

  const stopReplay = async () => {
    const current = simulation?.currentMs
    try { await stopSimulation() } catch { /* preserve the last displayed replay time */ }
    setSimulation(null)
    if (current != null) {
      const value = new Date(current).toISOString()
      setPinnedEndState(value)
      const url = new URL(window.location)
      url.searchParams.set('end', value)
      window.history.replaceState({}, '', url)
    }
  }

  useEffect(() => {
    const handlePop = () => {
      stopSimulation().catch(() => {})
      setSimulation(null)
      setPinnedEndState(getUrlEnd())
    }
    window.addEventListener('popstate', handlePop)
    return () => window.removeEventListener('popstate', handlePop)
  }, [])

  // refresh rates: pinned data never changes, so it is fetched once
  const isStreaming = live || Boolean(simulation?.playing)
  const fast = isStreaming ? 3000 : 0
  const medium = isStreaming ? 5000 : 0
  const slow = isStreaming ? 60000 : 0
  const alertRefresh = isStreaming ? 3000 : 0
  // Forecasting is expensive; keep its reference time fixed for the duration of playback.
  const forecastEnd = simulation ? new Date(simulation.endMs).toISOString() : end

  const health = usePolling(getHealth, [], 10000)
  const simulationStatus = usePolling(getSimulationStatus, [!!simulation], simulation?.playing || simulation?.failed ? 1000 : 0)
  const config = usePolling(getConfig, [], 0)
  const failures = usePolling(getFailures, [], 0)
  const latest = usePolling(() => getLatest(end), [end], live ? 3000 : 0)

  useEffect(() => {
    if (simulation || simulationStarting || !simulationStatus.data?.start || !simulationStatus.data?.end) return
    const { status, start, end: finish, sensor_time: sensorTime, speed } = simulationStatus.data
    if (['running', 'draining', 'failed', 'incomplete', 'completed'].includes(status)) {
      const isActive = ['running', 'draining'].includes(status)
      setSimulation({
        startMs: Date.parse(start), endMs: Date.parse(finish),
        currentMs: status === 'completed' ? Date.parse(finish) : Date.parse(sensorTime || start),
        speed: speed || SIM_SPEED, playing: isActive,
        failed: ['failed', 'incomplete'].includes(status),
      })
    }
  }, [simulation, simulationStarting, simulationStatus.data])

  useEffect(() => {
    if (!simulation?.playing) return
    if (['failed', 'incomplete'].includes(simulationStatus.data?.status)) {
      setSimulation((current) => current ? { ...current, playing: false, failed: true } : null)
      return
    }
    const availableMs = simulationStatus.data?.sensor_time ? Date.parse(simulationStatus.data.sensor_time) : null
    if (simulationStatus.data?.status === 'completed' && availableMs != null) {
      setSimulation((current) => current ? { ...current, currentMs: current.endMs, playing: false } : null)
    } else if (availableMs != null && availableMs > simulation.currentMs) {
      setSimulation((current) => current ? { ...current, currentMs: Math.min(availableMs, current.endMs) } : null)
    }
  }, [simulation?.playing, simulation?.currentMs, simulation?.endMs, simulationStatus.data])

  const apiOk = !health.error
  const cfg = config.data
  const fail = failures.data || []

  return (
    <div className="app">
      <Header
        apiOk={apiOk}
        latest={latest.data}
        failures={fail}
        live={live}
        pinnedEnd={pinnedEnd}
        onLive={() => setPinnedEnd(null)}
        onPin={setPinnedEnd}
        simulation={simulation}
        simulationStarting={simulationStarting}
        simulationStatus={simulationStatus.data}
        onSimulate={beginSimulation}
        onStopSimulation={stopReplay}
      />

      {!apiOk && (
        <div className="banner error big">
          Problem with the API at {API_URL}: {health.error}. Start it with <code>uvicorn backend.main:app --reload</code> and check that the database is running. This page retries automatically.
        </div>
      )}

      <main className="grid">
        <Card
          className="span-4"
          title="Failure risk"
          subtitle={`Model score for a failure within ${cfg?.failure_horizon_hours ?? 6} h (not a calibrated probability)`}
          loading={latest.loading && !latest.data}
          error={latest.error}
        >
          <RiskGauge value={latest.data?.predictions?.failure_risk?.score} threshold={cfg?.failure_threshold} />
          <Stats latest={latest.data} config={cfg} />
        </Card>

        <AnomalyChart className="span-8" end={end} refreshMs={fast} config={cfg} failures={fail} />
        <SensorChart className="span-12" end={end} refreshMs={fast} failures={fail} showAllSensors={!!simulation} />
        <ForecastChart className="span-7" end={forecastEnd} refreshMs={slow} config={cfg} />
        <AlertTable className="span-5" refreshMs={alertRefresh} onPin={setPinnedEnd} />
        <TwinPlaceholder className="span-12" />
      </main>

      <footer className="foot muted">
        Scores for past data come from models trained on the same period, so they are for demonstration. Model performance is reported in the notebooks.
      </footer>
    </div>
  )
}
