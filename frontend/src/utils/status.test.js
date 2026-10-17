import { computeStatus } from './status'

const preds = (risk, iforest, lstm) => ({
  predictions: {
    failure_risk: { flag: risk },
    iforest: { flag: iforest },
    ...(lstm === undefined ? {} : { lstm_ae: { flag: lstm } }),
  },
})

describe('computeStatus', () => {
  it('is offline when the API is down', () => {
    expect(computeStatus(preds(true, true), false).level).toBe('offline')
  })
  it('has no scores before the first prediction', () => {
    expect(computeStatus(null, true).level).toBe('unknown')
    expect(computeStatus({ predictions: {} }, true).level).toBe('unknown')
  })
  it('is healthy when nothing is flagged', () => {
    expect(computeStatus(preds(false, false), true).level).toBe('healthy')
  })
  it('is watch when exactly one kind of model flags', () => {
    expect(computeStatus(preds(true, false), true).level).toBe('watch')
    expect(computeStatus(preds(false, true), true).level).toBe('watch')
    expect(computeStatus(preds(false, false, true), true).level).toBe('watch')
  })
  it('is alert when risk and anomaly both flag', () => {
    expect(computeStatus(preds(true, true), true).level).toBe('alert')
    expect(computeStatus(preds(true, false, true), true).level).toBe('alert')
  })
})
