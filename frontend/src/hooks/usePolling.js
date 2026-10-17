import { useEffect, useRef, useState } from 'react'

export function errorMessage(e) {
  const detail = e?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (detail) return JSON.stringify(detail).slice(0, 200)
  if (e?.code === 'ERR_NETWORK') return 'Cannot reach the API. Is uvicorn running?'
  return e?.message || 'Request failed'
}

/**
 * Calls `fetcher` now and then every `intervalMs` (0 = only once).
 * - the next call starts only after the previous one finished (no overlapping requests)
 * - old data stays on screen if a refresh fails, with the error shown next to it
 * - when `deps` change (for example the pinned time), the data is cleared and fetched again
 * - after a failure a one-shot call retries every `retryMs`
 */
export default function usePolling(fetcher, deps = [], intervalMs = 0, retryMs = 5000) {
  const [state, setState] = useState({ data: null, error: null, loading: true })
  const fetcherRef = useRef(fetcher)
  useEffect(() => {
    fetcherRef.current = fetcher
  })

  useEffect(() => {
    let cancelled = false
    let timer
    setState({ data: null, error: null, loading: true })

    const run = async () => {
      let failed = false
      try {
        const data = await fetcherRef.current()
        if (!cancelled) setState({ data, error: null, loading: false })
      } catch (e) {
        failed = true
        if (!cancelled) setState((s) => ({ data: s.data, error: errorMessage(e), loading: false }))
      }
      if (!cancelled) {
        const next = failed ? intervalMs || retryMs : intervalMs
        if (next) timer = setTimeout(run, next)
      }
    }
    run()

    return () => {
      cancelled = true
      clearTimeout(timer)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, intervalMs])

  return state
}
