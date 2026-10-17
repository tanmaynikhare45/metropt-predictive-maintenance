/**
 * Overall status from the newest stored scores.
 *   alert   : the failure-risk model AND an anomaly model flag the newest window
 *   watch   : exactly one of them flags it
 *   healthy : nothing flagged
 * The flags come from the API (score above the model's threshold). Sustained-alert logic
 * (3 windows in a row) is applied when alerts are created in Phase 6.
 */
export function computeStatus(latest, apiOk) {
  if (!apiOk) return { level: 'offline', label: 'Offline' }
  const preds = latest?.predictions
  if (!preds || Object.keys(preds).length === 0) return { level: 'unknown', label: 'No scores yet' }

  const riskFlag = Boolean(preds.failure_risk?.flag)
  const anomalyFlag = Boolean(preds.iforest?.flag || preds.lstm_ae?.flag)
  if (riskFlag && anomalyFlag) return { level: 'alert', label: 'Alert' }
  if (riskFlag || anomalyFlag) return { level: 'watch', label: 'Watch' }
  return { level: 'healthy', label: 'Healthy' }
}

// colour band of the gauge: green below half the threshold, amber up to it, red above it
export function riskLevel(value, threshold) {
  if (value == null) return 'unknown'
  if (value > threshold) return 'alert'
  if (value > threshold / 2) return 'watch'
  return 'healthy'
}
