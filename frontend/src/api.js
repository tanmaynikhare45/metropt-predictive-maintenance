import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

export const getHealth = async () => {
  const { data } = await client.get('/health');
  return data;
};

export const getLatest = async (end = null) => {
  const params = end ? { end } : {};
  const { data } = await client.get('/latest', { params });
  return data;
};

export const getSensors = async ({
  hours = 6,
  bucket_minutes = 1,
  sensors = 'tp2,tp3,h1,dv_pressure,reservoirs,oil_temperature,motor_current',
  end = null,
} = {}) => {
  const params = { hours, bucket_minutes, sensors };
  if (end) params.end = end;
  const { data } = await client.get('/sensors', { params });
  return data;
};

export const getPredictions = async ({ model = 'iforest', hours = 24, end = null } = {}) => {
  const params = { model, hours };
  if (end) params.end = end;
  const { data } = await client.get('/predictions', { params });
  return data;
};

export const getFailures = async () => {
  const { data } = await client.get('/failures');
  return data;
};

export const getAlerts = async (limit = 30) => {
  const { data } = await client.get('/alerts', { params: { limit } });
  return data;
};

export const getForecast = async (sensor = 'TP2', end = null) => {
  const params = { sensor };
  if (end) params.end = end;
  const { data } = await client.get('/forecast', { params });
  return data;
};

export default client;
