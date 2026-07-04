import { useEffect, useRef, useState } from 'react'
import { geocode } from '../api/route'
import type { GeocodeResult } from '../api/route'

interface UseGeocodeOptions {
  enabled?: boolean
  delayMs?: number
  limit?: number
  minLength?: number
}

interface UseGeocodeResult {
  suggestions: GeocodeResult[]
  loading: boolean
  clear: () => void
}

// 無効時に毎レンダー新しい配列参照を返すと、呼び出し側の参照比較(例: 選択中インデックスのリセット)が
// 無限に再レンダーを誘発しうるため、安定した空配列を使い回す。
const EMPTY_SUGGESTIONS: GeocodeResult[] = []

/**
 * 住所入力のデバウンス付きサジェスト。300ms(既定)の入力停止後に GET /api/geocode を呼び出す。
 */
export function useGeocode(query: string, options: UseGeocodeOptions = {}): UseGeocodeResult {
  const { enabled = true, delayMs = 300, limit = 5, minLength = 2 } = options
  const [suggestions, setSuggestions] = useState<GeocodeResult[]>([])
  const [loading, setLoading] = useState(false)
  const requestId = useRef(0)

  const trimmed = query.trim()
  const shouldQuery = enabled && trimmed.length >= minLength

  useEffect(() => {
    if (!shouldQuery) {
      // クエリ未満/無効時は何もフェッチしない（表示側で空扱いにする）
      requestId.current += 1
      return
    }

    const currentId = ++requestId.current
    // setState はコールバック内でのみ呼ぶ（effect本体で直接呼ばない）ため、
    // ローディング開始も0msタイマー経由にする。
    const startTimer = setTimeout(() => {
      if (requestId.current === currentId) {
        setLoading(true)
      }
    }, 0)
    const timer = setTimeout(() => {
      geocode(trimmed, limit)
        .then((results) => {
          if (requestId.current === currentId) {
            setSuggestions(results)
          }
        })
        .catch(() => {
          if (requestId.current === currentId) {
            setSuggestions([])
          }
        })
        .finally(() => {
          if (requestId.current === currentId) {
            setLoading(false)
          }
        })
    }, delayMs)

    return () => {
      clearTimeout(startTimer)
      clearTimeout(timer)
    }
  }, [shouldQuery, trimmed, delayMs, limit])

  function clear() {
    requestId.current += 1
    setSuggestions([])
    setLoading(false)
  }

  return {
    suggestions: shouldQuery ? suggestions : EMPTY_SUGGESTIONS,
    loading: shouldQuery ? loading : false,
    clear,
  }
}
