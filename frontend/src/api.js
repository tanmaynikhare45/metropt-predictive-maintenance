// One function per backend endpoint. `end` (optional ISO string) pins the view to a point in time.
import axios from 'axios'

export const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

const http = axios.create({ baseURL: API_URL, timeout: 60000 })   // the first forecast can take a few seconds

const withEnd = (end) => (end ? { end } : {})
const get = (path, params) => http.get(path, { params }).then((r) => r.data)

export const getHealth = () => get('/health')
export const getConfig = () => get('/config')
export const getFailures = () => get('/failures')
export const getLatest = (end) => get('/latest', withEnd(end))
export const getAlerts = (limit = 20) => get('/alerts', { limit })

export const getSensors = ({ hours, bucket, sensors, end }) =>
  get('/sensors', { hours, bucket_minutes: bucket, sensors: sensors.join(','), ...withEnd(end) })

export const getPredictions = ({ model, hours, end }) =>
  get('/predictions', { model, hours, ...withEnd(end) })

export const getForecast = ({ sensor, end }) => get('/forecast', { sensor, ...withEnd(end) })
