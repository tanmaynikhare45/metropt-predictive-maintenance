import { useEffect, useState } from 'react'
import { API_URL, getConfig, getFailures, getHealth, getLatest } from './api'
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

function getUrlEnd() {
  const params = new URLSearchParams(window.location.search)
  const val = params.get('end')
  return val ? val.trim() : null
}

export default function App() {
  // Live: no `end`, the API anchors at the newest reading. Pinned: every request gets end=<time>.
  // Check URL query param (e.g. from Slack alert links: /?end=2020-06-05T06:50:00Z)
  const [pinnedEnd, setPinnedEndState] = useState(getUrlEnd)
  const end = pinnedEnd || undefined
  const live = !pinnedEnd

  const setPinnedEnd = (val) => {
    setPinnedEndState(val)
    const url = new URL(window.location)
    if (val) {
      url.searchParams.set('end', val)
    } else {
      url.searchParams.delete('end')
    }
    window.history.replaceState({}, '', url)
  }

  useEffect(() => {
    const handlePop = () => {
      setPinnedEndState(getUrlEnd())
    }
    window.addEventListener('popstate', handlePop)
    return () => window.removeEventListener('popstate', handlePop)
  }, [])

  // refresh rates: pinned data never changes, so it is fetched once
  const fast = live ? 5000 : 0
  const medium = live ? 10000 : 0
  const slow = live ? 60000 : 0

  const health = usePolling(getHealth, [], 10000)
  const config = usePolling(getConfig, [], 0)
  const failures = usePolling(getFailures, [], 0)
  const latest = usePolling(() => getLatest(end), [end], live ? 3000 : 0)

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
        <SensorChart className="span-12" end={end} refreshMs={fast} failures={fail} />
        <ForecastChart className="span-7" end={end} refreshMs={slow} config={cfg} />
        <AlertTable className="span-5" refreshMs={medium} onPin={setPinnedEnd} />
        <TwinPlaceholder className="span-12" />
      </main>

      <footer className="foot muted">
        Scores for past data come from models trained on the same period, so they are for demonstration. Model performance is reported in the notebooks.
      </footer>
    </div>
  )
}
