import { useCallback, useState } from 'react'
import { createRoute } from '../api/route'
import type { AddressPoint, RouteResponse } from '../api/route'

export type RouteStatus = 'idle' | 'loading' | 'success' | 'error'

interface UseRouteResult {
  route: RouteResponse | null
  status: RouteStatus
  error: string | null
  search: (origin: AddressPoint, destination: AddressPoint) => Promise<RouteResponse>
  reset: () => void
}

/**
 * POST /api/route の呼び出しと状態管理。API失敗時に偽データへフォールバックはしない
 * （呼び出し側でエラーバナー+再試行ボタンを表示する）。
 */
export function useRoute(): UseRouteResult {
  const [route, setRoute] = useState<RouteResponse | null>(null)
  const [status, setStatus] = useState<RouteStatus>('idle')
  const [error, setError] = useState<string | null>(null)

  const search = useCallback(async (origin: AddressPoint, destination: AddressPoint) => {
    setStatus('loading')
    setError(null)
    try {
      const response = await createRoute(origin, destination)
      setRoute(response)
      setStatus('success')
      return response
    } catch (err) {
      const message = err instanceof Error ? err.message : 'ルート検索に失敗しました'
      setStatus('error')
      setError(message)
      throw err
    }
  }, [])

  const reset = useCallback(() => {
    setRoute(null)
    setStatus('idle')
    setError(null)
  }, [])

  return { route, status, error, search, reset }
}
