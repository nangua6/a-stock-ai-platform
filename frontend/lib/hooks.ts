'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import type { DataMeta, DataState } from './types'

interface UseApiResult<T> {
  data: T | null
  meta: DataMeta
  refetch: () => void
}

/**
 * Generic hook for API calls with loading/error/retry states.
 */
export function useApi<T>(
  fetcher: () => Promise<T>,
  deps: unknown[] = [],
): UseApiResult<T> {
  const [data, setData] = useState<T | null>(null)
  const [meta, setMeta] = useState<DataMeta>({ state: 'LOADING' })
  const mountedRef = useRef(true)

  const fetchData = useCallback(async () => {
    setMeta(prev => ({ ...prev, state: 'LOADING' as DataState }))
    try {
      const result = await fetcher()
      if (!mountedRef.current) return
      setData(result)
      setMeta({
        state: 'SUCCESS' as DataState,
        timestamp: new Date().toISOString(),
        source: 'api',
      })
    } catch (err) {
      if (!mountedRef.current) return
      const message = err instanceof Error ? err.message : 'Unknown error'
      setMeta({
        state: 'ERROR' as DataState,
        error: message,
      })
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  useEffect(() => {
    mountedRef.current = true
    fetchData()
    return () => { mountedRef.current = false }
  }, [fetchData])

  return { data, meta, refetch: fetchData }
}

/**
 * Hook for periodic auto-refresh.
 */
export function useAutoRefresh<T>(
  fetcher: () => Promise<T>,
  intervalMs: number,
  deps: unknown[] = [],
): UseApiResult<T> {
  const result = useApi(fetcher, deps)

  useEffect(() => {
    const timer = setInterval(() => {
      result.refetch()
    }, intervalMs)
    return () => clearInterval(timer)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intervalMs, result.refetch])

  return result
}
