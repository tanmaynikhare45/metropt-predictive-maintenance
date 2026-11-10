export const SENSORS = [
  { key: 'tp2', label: 'TP2' },
  { key: 'tp3', label: 'TP3' },
  { key: 'h1', label: 'H1' },
  { key: 'dv_pressure', label: 'DV pressure' },
  { key: 'reservoirs', label: 'Reservoirs' },
  { key: 'oil_temperature', label: 'Oil temperature' },
  { key: 'motor_current', label: 'Motor current' },
  { key: 'comp', label: 'COMP' },
  { key: 'dv_eletric', label: 'DV electric' },
  { key: 'towers', label: 'Towers' },
  { key: 'mpg', label: 'MPG' },
  { key: 'lps', label: 'LPS' },
  { key: 'pressure_switch', label: 'Pressure switch' },
  { key: 'oil_level', label: 'Oil level' },
  { key: 'caudal_impulses', label: 'Caudal impulses' },
]

export const MAX_POINTS = 300

// keep every chart under ~300 points: the browser stays fast and the lines stay readable
export const bucketFor = (hours) => Math.max(1, Math.ceil((hours * 60) / MAX_POINTS))
