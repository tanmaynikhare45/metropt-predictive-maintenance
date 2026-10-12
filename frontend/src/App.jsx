import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import SystemOverviewCards from './components/SystemOverviewCards';
import SensorTelemetryChart from './components/SensorTelemetryChart';
import PredictionsChart from './components/PredictionsChart';
import ForecastPanel from './components/ForecastPanel';
import DigitalTwinQuickView from './components/DigitalTwinQuickView';
import AlertsTable from './components/AlertsTable';
import {
  getHealth,
  getLatest,
  getSensors,
  getPredictions,
  getAlerts,
} from './api';

export default function App() {
  const [health, setHealth] = useState(null);
  const [latestData, setLatestData] = useState(null);
  const [sensorRows, setSensorRows] = useState([]);
  const [iforestRows, setIforestRows] = useState([]);
  const [riskRows, setRiskRows] = useState([]);
  const [alerts, setAlerts] = useState([]);

  const [timeRange, setTimeRange] = useState(6); // hours
  const [refreshInterval, setRefreshInterval] = useState(3000); // 3 seconds
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  const fetchData = useCallback(async () => {
    setIsRefreshing(true);
    try {
      // 1. Health check
      const healthRes = await getHealth().catch(() => ({ status: 'error' }));
      setHealth(healthRes);

      // 2. Latest reading & predictions
      const latestRes = await getLatest().catch(() => null);
      if (latestRes) {
        setLatestData(latestRes);
      }

      // Determine bucket minutes based on time range to prevent slow charts
      const bucketMins = timeRange <= 2 ? 1 : timeRange <= 6 ? 2 : timeRange <= 12 ? 5 : 10;

      // 3. Fetch Sensors
      const sensorsRes = await getSensors({
        hours: timeRange,
        bucket_minutes: bucketMins,
      }).catch(() => []);
      setSensorRows(sensorsRes);

      // 4. Fetch Predictions (iforest and failure_risk)
      const [ifRes, riskRes] = await Promise.all([
        getPredictions({ model: 'iforest', hours: timeRange }).catch(() => []),
        getPredictions({ model: 'failure_risk', hours: timeRange }).catch(() => []),
      ]);
      setIforestRows(ifRes);
      setRiskRows(riskRes);

      // 5. Fetch Alerts
      const alertsRes = await getAlerts(20).catch(() => []);
      setAlerts(alertsRes);

      setErrorMessage(null);
    } catch (err) {
      console.error('Fetch error:', err);
      setErrorMessage('Unable to connect to FastAPI backend at http://127.0.0.1:8000');
    } finally {
      setIsRefreshing(false);
    }
  }, [timeRange]);

  // Initial load and interval polling
  useEffect(() => {
    fetchData();

    if (refreshInterval > 0) {
      const timer = setInterval(fetchData, refreshInterval);
      return () => clearInterval(timer);
    }
  }, [fetchData, refreshInterval]);

  return (
    <div className="dashboard-container">
      {/* 1. Header with System Health & Global Controls */}
      <Header
        health={health}
        latestTime={latestData?.sensors?.time}
        isRefreshing={isRefreshing}
        refreshInterval={refreshInterval}
        setRefreshInterval={setRefreshInterval}
        onManualRefresh={fetchData}
        timeRange={timeRange}
        setTimeRange={setTimeRange}
      />

      {/* Backend Connection Alert if down */}
      {errorMessage && (
        <div style={{
          background: 'rgba(244, 63, 94, 0.15)',
          border: '1px solid rgba(244, 63, 94, 0.4)',
          borderRadius: 'var(--radius-sm)',
          padding: '0.75rem 1.25rem',
          color: '#fb7185',
          fontSize: '0.85rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <span>⚠️ {errorMessage}. Please ensure <code>uvicorn backend.main:app --reload</code> is running.</span>
          <button
            onClick={fetchData}
            style={{ background: 'none', border: '1px solid #fb7185', color: '#fb7185', padding: '0.2rem 0.6rem', borderRadius: '4px', cursor: 'pointer', fontSize: '0.75rem' }}
          >
            Retry
          </button>
        </div>
      )}

      {/* 2. Key Performance Indicators & APU Overview */}
      <SystemOverviewCards
        latestData={latestData}
      />

      {/* 3. Primary Telemetry & Digital Twin Layout */}
      <div className="grid-main-charts">
        <SensorTelemetryChart
          data={sensorRows}
          loading={isRefreshing && sensorRows.length === 0}
        />
        <DigitalTwinQuickView
          latestSensors={latestData?.sensors || {}}
        />
      </div>

      {/* 4. Machine Learning & Forecasting Panels */}
      <div className="grid-secondary-panels">
        <PredictionsChart
          iforestData={iforestRows}
          failureRiskData={riskRows}
          threshold={0.50}
        />
        <ForecastPanel />
      </div>

      {/* 5. Alerts and Diagnostics Log */}
      <AlertsTable
        alerts={alerts}
      />
    </div>
  );
}
