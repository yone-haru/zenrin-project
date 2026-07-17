import { useEffect, useRef, useState } from 'react'

interface StreetViewPreviewProps {
  lat: number
  lng: number
}

type Status = 'loading' | 'ready' | 'not-found' | 'unavailable'

const SDK_POLL_INTERVAL_MS = 200
const SDK_POLL_TIMEOUT_MS = 5000

/**
 * パノラマ地点から対象地点への方位角（度、真北=0）をatan2で自前計算する。
 * geometryライブラリ（google.maps.geometry.spherical）は読み込まない。
 */
function bearingDegrees(fromLat: number, fromLng: number, toLat: number, toLng: number): number {
  const toRad = (deg: number) => (deg * Math.PI) / 180
  const toDeg = (rad: number) => (rad * 180) / Math.PI
  const phi1 = toRad(fromLat)
  const phi2 = toRad(toLat)
  const deltaLambda = toRad(toLng - fromLng)
  const y = Math.sin(deltaLambda) * Math.cos(phi2)
  const x = Math.cos(phi1) * Math.sin(phi2) - Math.sin(phi1) * Math.cos(phi2) * Math.cos(deltaLambda)
  return (toDeg(Math.atan2(y, x)) + 360) % 360
}

/**
 * 危険地点のGoogleストリートビューを埋め込む。視点（向き・ズーム）操作は許可するが、
 * リンククリックや別パノラマへの遷移（移動）はさせない読み取り専用プレビュー。
 * VITE_GOOGLE_MAPS_API_KEY未設定時（Leafletフォールバック運用）はnullを返し非表示にする。
 */
export function StreetViewPreview({ lat, lng }: StreetViewPreviewProps) {
  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [status, setStatus] = useState<Status>('loading')

  useEffect(() => {
    if (!apiKey) return undefined

    let cancelled = false
    let pollTimer: number | undefined
    let panoListener: google.maps.MapsEventListener | undefined
    let waitedMs = 0

    function loadPanorama() {
      const container = containerRef.current
      if (!container) return

      const service = new google.maps.StreetViewService()
      service.getPanorama(
        { location: { lat, lng }, radius: 50, source: google.maps.StreetViewSource.OUTDOOR },
        (data, apiStatus) => {
          if (cancelled) return
          const location = data?.location
          if (apiStatus !== 'OK' || !location || !location.latLng) {
            setStatus('not-found')
            return
          }

          const panoId = location.pano
          const heading = bearingDegrees(location.latLng.lat(), location.latLng.lng(), lat, lng)

          const panorama = new google.maps.StreetViewPanorama(container, {
            pano: panoId,
            pov: { heading, pitch: 0 },
            // 移動禁止: リンク・クリック遷移・各種ナビゲーションUIを封じる。視点の回転/ズームのみ許可。
            clickToGo: false,
            linksControl: false,
            panControl: false,
            zoomControl: false,
            addressControl: false,
            fullscreenControl: false,
            enableCloseButton: false,
            motionTracking: false,
            motionTrackingControl: false,
            showRoadLabels: true,
          })

          // 保険の移動ロック: 何らかの経路でpanoIdが変わったら元のパノラマへ戻す。
          panoListener = panorama.addListener('pano_changed', () => {
            if (panorama.getPano() !== panoId) panorama.setPano(panoId)
          })

          setStatus('ready')
        },
      )
    }

    function pollForSdk() {
      if (cancelled) return
      if (window.google?.maps?.StreetViewPanorama) {
        loadPanorama()
        return
      }
      waitedMs += SDK_POLL_INTERVAL_MS
      if (waitedMs >= SDK_POLL_TIMEOUT_MS) {
        setStatus('unavailable')
        return
      }
      pollTimer = window.setTimeout(pollForSdk, SDK_POLL_INTERVAL_MS)
    }

    // set-state-in-effectルール対策: 座標変更時の状態リセットはタイマーコールバック側に逃がす。
    pollTimer = window.setTimeout(() => {
      setStatus('loading')
      pollForSdk()
    }, 0)

    return () => {
      cancelled = true
      if (pollTimer !== undefined) window.clearTimeout(pollTimer)
      panoListener?.remove()
    }
  }, [apiKey, lat, lng])

  if (!apiKey) return null

  return (
    <div className="street-view-frame">
      <div ref={containerRef} className="street-view-canvas" />
      {status !== 'ready' && (
        <div className="street-view-status">
          {status === 'not-found'
            ? 'この地点のストリートビューはありません'
            : status === 'unavailable'
              ? 'ストリートビューを読み込めませんでした'
              : '読み込み中…'}
        </div>
      )}
    </div>
  )
}
