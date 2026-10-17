import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import * as api from './api'
import App from './App'

// Recharts needs real element sizes, which jsdom does not have: give charts a fixed size.
vi.mock('recharts', async (importOriginal) => {
  const mod = await importOriginal()
  const React = await import('react')
  return {
    ...mod,
    ResponsiveContainer: ({ children }) => React.cloneElement(children, { width: 600, height: 240 }),
  }
})

vi.mock('./api', () => ({
  API_URL: 'http://test',
  getHealth: vi.fn(),
  getConfig: vi.fn(),
  getFailures: vi.fn(),
  getLatest: vi.fn(),
  getSensors: vi.fn(),
  getPredictions: vi.fn(),
  getForecast: vi.fn(),
  getAlerts: vi.fn(),
}))

const t0 = Date.parse('2020-06-05T06:00:00Z')
const iso = (i, step = 60000) => new Date(t0 + i * step).toISOString()

const latest = {
  sensors: { time: '2020-06-05T08:00:00Z', tp2: 9.1 },
  predictions: {
    iforest: { time: '2020-06-05T07:50:00Z', score: 0.62, flag: true },
    failure_risk: { time: '2020-06-05T07:50:00Z', score: 0.71, flag: true },
  },
}
const config = {
  iforest_threshold: 0.55, lstm_threshold: null, failure_threshold: 0.5, failure_horizon_hours: 6,
  forecast_sensors: ['TP2', 'Oil_temperature'], forecast_interval: 0.9,
}
const failures = [
  { id: 1, start_time: '2020-06-05T10:00:00+00:00', end_time: '2020-06-07T14:30:00+00:00' },
  { id: 2, start_time: '2020-07-15T14:30:00+00:00', end_time: '2020-07-15T19:00:00+00:00' },
]

beforeEach(() => {
  api.getHealth.mockResolvedValue({ status: 'ok' })
  api.getConfig.mockResolvedValue(config)
  api.getFailures.mockResolvedValue(failures)
  api.getLatest.mockResolvedValue(latest)
  api.getSensors.mockImplementation(async ({ sensors }) =>
    Array.from({ length: 60 }, (_, i) => ({ time: iso(i), ...Object.fromEntries(sensors.map((s) => [s, 5 + Math.sin(i / 5)])) })))
  api.getPredictions.mockImplementation(async () =>
    Array.from({ length: 60 }, (_, i) => ({ time: iso(i, 600000), score: 0.3 + i / 100, flag: i > 40 })))
  api.getForecast.mockResolvedValue({
    sensor: 'TP2', method: 'prophet_level',
    history: Array.from({ length: 144 }, (_, i) => ({ time: iso(i, 600000), value: 5 + Math.sin(i / 10) })),
    forecast: Array.from({ length: 36 }, (_, i) => ({ time: iso(144 + i, 600000), yhat: 5, lower: 4.5, upper: 5.5 })),
  })
  api.getAlerts.mockResolvedValue([])
})

afterEach(() => vi.clearAllMocks())

describe('dashboard', () => {
  it('shows status, gauge, stats and an empty alert table', async () => {
    render(<App />)
    expect(await screen.findByText('Alert', { exact: true })).toBeTruthy()          // both models flag -> Alert
    expect(await screen.findByRole('img', { name: /Failure risk 71 percent/ })).toBeTruthy()
    expect(await screen.findByText('0.710')).toBeTruthy()                           // risk score in the stats
    expect(await screen.findByText(/No alerts yet/)).toBeTruthy()
    expect(screen.getByText(/Coming in Phase 7/)).toBeTruthy()
  })

  it('renders the charts without errors', async () => {
    const { container } = render(<App />)
    await waitFor(() => expect(container.querySelectorAll('.recharts-line').length).toBeGreaterThan(4))
    expect(container.querySelectorAll('.recharts-reference-area').length).toBeGreaterThan(0)   // failure shading
    expect(await screen.findByText(/method: prophet_level/)).toBeTruthy()
  })

  it('pins every request to a time before the failure', async () => {
    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: 'Failure 1' }))
    await waitFor(() => expect(api.getLatest).toHaveBeenLastCalledWith('2020-06-05T07:00:00.000Z'))
    await waitFor(() => expect(api.getPredictions).toHaveBeenLastCalledWith(expect.objectContaining({ end: '2020-06-05T07:00:00.000Z' })))
    expect(await screen.findByText('Pinned to (UTC)')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Live' }))
    await waitFor(() => expect(api.getLatest).toHaveBeenLastCalledWith(undefined))
  })

  it('jumps to a chosen offset from the failure start', async () => {
    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: '6 h after' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Failure 1' }))
    await waitFor(() => expect(api.getLatest).toHaveBeenLastCalledWith('2020-06-05T16:00:00.000Z'))
  })

  it('shows an offline banner and keeps the page usable when the API is down', async () => {
    api.getHealth.mockRejectedValue(new Error('Network Error'))
    render(<App />)
    expect(await screen.findByText(/Problem with the API at http:\/\/test/)).toBeTruthy()
    expect(await screen.findByText('Offline', { exact: true })).toBeTruthy()
  })

  it('lets the user switch the anomaly model', async () => {
    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: 'Failure risk' }))
    await waitFor(() => expect(api.getPredictions).toHaveBeenLastCalledWith(expect.objectContaining({ model: 'failure_risk' })))
  })
})
