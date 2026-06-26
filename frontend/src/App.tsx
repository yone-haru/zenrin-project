import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { useEffect, useMemo, useState } from 'react'
import type { CSSProperties } from 'react'
import { MapContainer, Marker, Polyline, TileLayer, useMap, useMapEvents } from 'react-leaflet'
import { createRoute, geocodeAddress } from './api/route'
import type { HazardPoint, RouteResponse } from './api/route'

const NAGASAKI_CENTER: [number, number] = [32.7503, 129.8777]

type Point = { lat: number; lng: number; address: string }
type Target = 'origin' | 'destination'

const DEMO_ORIGIN: Point = { lat: 32.7503, lng: 129.8777, address: '長崎市立〇〇小学校' }
const DEMO_DESTINATION: Point = { lat: 32.7601, lng: 129.869, address: '〇〇町1-2-3' }

function riskColor(score: number) {
  if (score >= 4) return '#ef4444'
  if (score === 3) return '#f97316'
  return '#eab308'
}

function riskSoftColor(score: number) {
  if (score >= 4) return '#fee2e2'
  if (score === 3) return '#ffedd5'
  return '#fef3c7'
}

function readableRiskText(score: number) {
  return score <= 2 ? '#422006' : '#ffffff'
}

function formatDistance(meters: number) {
  return meters >= 1000 ? `${(meters / 1000).toFixed(1)}km` : `${Math.round(meters)}m`
}

function formatDuration(seconds: number) {
  return `約${Math.max(1, Math.round(seconds / 60))}分`
}

function makeDemoRoute(origin: Point, destination: Point): RouteResponse {
  const coordinates: [number, number][] = [
    [origin.lng, origin.lat],
    [129.8752, 32.7524],
    [129.8726, 32.7557],
    [129.8708, 32.7581],
    [destination.lng, destination.lat],
  ]

  const hazards: HazardPoint[] = [
    {
      id: 'honkochi-crossing',
      title: '本河内交差点',
      latitude: 32.7524,
      longitude: 129.8752,
      risk_score: 5,
      risk_factors: ['歩道なし', '過去事故3件', '幹線道路との交差'],
      accident_count: 3,
      osm_tags: { highway: '幹線道路', sidewalk: 'なし' },
      distance_from_origin_m: 350,
    },
    {
      id: 'sakuramachi-bridge',
      title: '桜町歩道橋前',
      latitude: 32.7557,
      longitude: 129.8726,
      risk_score: 3,
      risk_factors: ['見通し不良', '横断歩道の間隔が広い'],
      accident_count: 1,
      osm_tags: { highway: '補助幹線道路', sidewalk: '片側のみ' },
      distance_from_origin_m: 720,
    },
    {
      id: 'sakaemachi-corner',
      title: '栄町2丁目角',
      latitude: 32.7581,
      longitude: 129.8708,
      risk_score: 2,
      risk_factors: ['車両の通行が多い'],
      accident_count: 0,
      osm_tags: { highway: '生活道路', sidewalk: 'あり' },
      distance_from_origin_m: 980,
    },
  ]

  return {
    route_geometry: { type: 'LineString', coordinates },
    distance_m: 1250,
    duration_s: 900,
    hazard_points: hazards,
  }
}

function pointIcon(label: 'A' | 'B', color: string) {
  return L.divIcon({
    className: '',
    iconSize: [34, 42],
    iconAnchor: [17, 39],
    html: `<div class="point-marker" style="--marker-color:${color}"><span>${label}</span></div>`,
  })
}

function hazardIcon(hazard: HazardPoint, selected: boolean) {
  const color = riskColor(hazard.risk_score)
  return L.divIcon({
    className: '',
    iconSize: selected ? [44, 44] : [36, 36],
    iconAnchor: selected ? [22, 22] : [18, 18],
    html: `<div class="hazard-marker ${selected ? 'is-selected' : ''}" style="--risk-color:${color};--risk-text:${readableRiskText(hazard.risk_score)}">${hazard.risk_score}</div>`,
  })
}

function routeCueIcon(angle: number, label?: string) {
  return L.divIcon({
    className: '',
    iconSize: label ? [116, 34] : [30, 30],
    iconAnchor: label ? [58, 17] : [15, 15],
    html: label
      ? `<div class="route-label">${label}</div>`
      : `<div class="route-cue" style="--route-angle:${angle}deg">➜</div>`,
  })
}

function bearing(from: [number, number], to: [number, number]) {
  const deltaLng = ((to[1] - from[1]) * Math.PI) / 180
  const lat1 = (from[0] * Math.PI) / 180
  const lat2 = (to[0] * Math.PI) / 180
  const y = Math.sin(deltaLng) * Math.cos(lat2)
  const x = Math.cos(lat1) * Math.sin(lat2) - Math.sin(lat1) * Math.cos(lat2) * Math.cos(deltaLng)
  return (Math.atan2(y, x) * 180) / Math.PI
}

function MapClickHandler({ onPick }: { onPick: (lat: number, lng: number) => void }) {
  useMapEvents({
    click(event) {
      onPick(event.latlng.lat, event.latlng.lng)
    },
  })
  return null
}

function FitRoute({ points }: { points: [number, number][] }) {
  const map = useMap()
  useEffect(() => {
    if (points.length > 1) {
      map.fitBounds(points, { paddingTopLeft: [390, 40], paddingBottomRight: [360, 40] })
    }
  }, [map, points])
  return null
}

function Icon({ name }: { name: 'shield' | 'search' | 'swap' | 'walk' | 'clock' | 'pin' | 'warning' }) {
  const paths = {
    shield: 'M12 3l7 3v5c0 4.5-2.8 8.4-7 10-4.2-1.6-7-5.5-7-10V6l7-3zm-3 9l2 2 4-5',
    search: 'M10.5 18a7.5 7.5 0 1 1 5.3-12.8A7.5 7.5 0 0 1 10.5 18zm5.2-2.3L21 21',
    swap: 'M8 4v14m0 0l-4-4m4 4l4-4m8 6V6m0 0l-4 4m4-4l4 4',
    walk: 'M13 4a2 2 0 1 1-4 0 2 2 0 0 1 4 0zm-2 4l-2 5 4 2 1 5m-5-7l-3 6m5-10l4 3',
    clock: 'M12 21a9 9 0 1 1 0-18 9 9 0 0 1 0 18zm0-13v5l3 2',
    pin: 'M12 21s7-5.1 7-11a7 7 0 1 0-14 0c0 5.9 7 11 7 11zm0-8.5a2.5 2.5 0 1 1 0-5 2.5 2.5 0 0 1 0 5z',
    warning: 'M12 3l10 18H2L12 3zm0 6v5m0 3h.01',
  }
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d={paths[name]} />
    </svg>
  )
}

function App() {
  const [origin, setOrigin] = useState<Point | null>(DEMO_ORIGIN)
  const [destination, setDestination] = useState<Point | null>(DEMO_DESTINATION)
  const [originText, setOriginText] = useState(DEMO_ORIGIN.address)
  const [destinationText, setDestinationText] = useState(DEMO_DESTINATION.address)
  const [nextPick, setNextPick] = useState<Target>('origin')
  const [route, setRoute] = useState<RouteResponse | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [modalId, setModalId] = useState<string | null>(null)
  const [status, setStatus] = useState<'idle' | 'loading' | 'error'>('idle')
  const [message, setMessage] = useState('地図をクリックして地点を指定できます')

  const routePositions = useMemo<[number, number][]>(() => {
    if (!route) return []
    return route.route_geometry.coordinates.map(([lng, lat]) => [lat, lng])
  }, [route])

  const routeCues = useMemo(() => {
    if (routePositions.length < 3) return []
    const cueCount = Math.min(5, routePositions.length - 2)
    return Array.from({ length: cueCount }, (_, index) => {
      const pointIndex = Math.max(1, Math.round(((index + 1) * (routePositions.length - 1)) / (cueCount + 1)))
      return {
        position: routePositions[pointIndex],
        angle: bearing(routePositions[pointIndex - 1], routePositions[Math.min(routePositions.length - 1, pointIndex + 1)]),
      }
    })
  }, [routePositions])

  const routeLabelPosition = routePositions[Math.floor(routePositions.length / 2)]

  const selectedHazard = route?.hazard_points.find((hazard) => hazard.id === modalId) ?? null

  async function resolvePoint(text: string, fallback: Point): Promise<Point> {
    if (!text.trim()) return fallback
    try {
      const result = await geocodeAddress(text)
      return { lat: result.lat, lng: result.lng, address: result.display_name }
    } catch {
      return { ...fallback, address: text }
    }
  }

  async function handleSearch() {
    setStatus('loading')
    setMessage('ルートを検索しています')

    const resolvedOrigin = await resolvePoint(originText, origin ?? DEMO_ORIGIN)
    const resolvedDestination = await resolvePoint(destinationText, destination ?? DEMO_DESTINATION)
    setOrigin(resolvedOrigin)
    setDestination(resolvedDestination)

    try {
      const response = await createRoute(resolvedOrigin, resolvedDestination)
      setRoute(response)
      setSelectedId(response.hazard_points[0]?.id ?? null)
      setStatus('idle')
      setMessage('ルート上の危険箇所を確認できます')
    } catch {
      const demo = makeDemoRoute(resolvedOrigin, resolvedDestination)
      setRoute(demo)
      setSelectedId(demo.hazard_points[0]?.id ?? null)
      setStatus('error')
      setMessage('APIに接続できないためデモデータを表示しています')
    }
  }

  function handlePick(lat: number, lng: number) {
    const point = { lat, lng, address: `地図指定 ${lat.toFixed(5)}, ${lng.toFixed(5)}` }
    if (nextPick === 'origin') {
      setOrigin(point)
      setOriginText(point.address)
      setNextPick('destination')
      setMessage('目的地を地図上で指定できます')
    } else {
      setDestination(point)
      setDestinationText(point.address)
      setNextPick('origin')
      setMessage('出発地と目的地を指定しました')
    }
  }

  function openHazard(hazard: HazardPoint) {
    setSelectedId(hazard.id)
    setModalId(hazard.id)
  }

  return (
    <main className="app-shell">
      <MapContainer center={NAGASAKI_CENTER} zoom={14} className="safety-map" zoomControl={false}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <MapClickHandler onPick={handlePick} />
        {routePositions.length > 0 && <FitRoute points={routePositions} />}
        {routePositions.length > 0 && (
          <>
            <Polyline positions={routePositions} pathOptions={{ color: '#0f172a', weight: 17, opacity: 0.18 }} />
            <Polyline positions={routePositions} pathOptions={{ color: '#ffffff', weight: 13, opacity: 0.98 }} />
            <Polyline positions={routePositions} pathOptions={{ color: '#2563eb', weight: 8, opacity: 1 }} />
            <Polyline
              positions={routePositions}
              pathOptions={{ color: '#93c5fd', weight: 2, opacity: 0.9, dashArray: '10 14' }}
            />
            {routeCues.map((cue, index) => (
              <Marker key={`route-cue-${index}`} position={cue.position} icon={routeCueIcon(cue.angle)} interactive={false} />
            ))}
            {routeLabelPosition && (
              <Marker position={routeLabelPosition} icon={routeCueIcon(0, '通学ルート')} interactive={false} />
            )}
          </>
        )}
        {origin && <Marker position={[origin.lat, origin.lng]} icon={pointIcon('A', '#16a34a')} />}
        {destination && <Marker position={[destination.lat, destination.lng]} icon={pointIcon('B', '#ef4444')} />}
        {route?.hazard_points.map((hazard) => (
          <Marker
            key={hazard.id}
            position={[hazard.latitude, hazard.longitude]}
            icon={hazardIcon(hazard, hazard.id === selectedId)}
            eventHandlers={{ click: () => openHazard(hazard) }}
          />
        ))}
      </MapContainer>

      <section className="search-card">
        <header className="brand-row">
          <span className="brand-icon">
            <Icon name="shield" />
          </span>
          <h1>通学路安全マップ</h1>
        </header>
        <div className="field-stack">
          <label>
            <span>出発地</span>
            <div className="input-shell origin-dot">
              <input value={originText} onChange={(event) => setOriginText(event.target.value)} placeholder="出発地を入力" />
            </div>
          </label>
          <button
            className="swap-button"
            type="button"
            aria-label="出発地と目的地を入れ替え"
            onClick={() => {
              setOrigin(destination)
              setDestination(origin)
              setOriginText(destinationText)
              setDestinationText(originText)
            }}
          >
            <Icon name="swap" />
          </button>
          <label>
            <span>目的地</span>
            <div className="input-shell destination-pin">
              <input
                value={destinationText}
                onChange={(event) => setDestinationText(event.target.value)}
                placeholder="目的地を入力"
              />
            </div>
          </label>
        </div>
        <button className="search-button" type="button" onClick={handleSearch} disabled={status === 'loading'}>
          <Icon name="search" />
          {status === 'loading' ? '検索中...' : 'ルートを検索'}
        </button>
      </section>

      {route && (
        <section className="route-card">
          <span className="label">ルート情報</span>
          <div className="route-metrics">
            <span>
              <Icon name="walk" />
              {formatDistance(route.distance_m)}
            </span>
            <span>
              <Icon name="clock" />
              {formatDuration(route.duration_s)}
            </span>
            <strong>危険箇所 {route.hazard_points.length}件</strong>
          </div>
        </section>
      )}

      {route && (
        <aside className="hazard-panel">
          <div className="panel-title">
            <h2>危険箇所一覧</h2>
            <span>{route.hazard_points.length}件</span>
          </div>
          <div className="hazard-list">
            {route.hazard_points.map((hazard) => (
              <button
                key={hazard.id}
                className={`hazard-item ${hazard.id === selectedId ? 'is-selected' : ''}`}
                style={{ borderLeftColor: riskColor(hazard.risk_score) }}
                type="button"
                onClick={() => openHazard(hazard)}
              >
                <span
                  className="score-badge"
                  style={{
                    backgroundColor: riskColor(hazard.risk_score),
                    color: readableRiskText(hazard.risk_score),
                  }}
                >
                  {hazard.risk_score}
                </span>
                <span className="hazard-summary">
                  <span className="hazard-title">{hazard.title ?? '危険地点'}</span>
                  <span className="hazard-distance">出発から{formatDistance(hazard.distance_from_origin_m ?? 0)}</span>
                  <span className="tag-row">
                    {hazard.risk_factors.slice(0, 2).map((factor) => (
                      <span key={factor}>{factor}</span>
                    ))}
                  </span>
                </span>
                <span className="chevron">›</span>
              </button>
            ))}
          </div>
        </aside>
      )}

      {!route && (
        <div className="hint-pill">
          <Icon name="pin" />
          {message}
        </div>
      )}
      {route && <div className={`status-pill ${status === 'error' ? 'is-warning' : ''}`}>{message}</div>}

      {selectedHazard && (
        <div className="modal-backdrop" onClick={() => setModalId(null)}>
          <article
            className="hazard-modal"
            style={{ '--risk-color': riskColor(selectedHazard.risk_score) } as CSSProperties}
            onClick={(event) => event.stopPropagation()}
          >
            <div className="modal-strip" />
            <button className="close-button" type="button" aria-label="閉じる" onClick={() => setModalId(null)}>
              ×
            </button>
            <span className="label">危険度</span>
            <div className="modal-score">
              <strong>{selectedHazard.risk_score}</strong>
              <span>
                {[1, 2, 3, 4, 5].map((value) => (
                  <i key={value} className={value <= selectedHazard.risk_score ? 'filled' : ''} />
                ))}
              </span>
            </div>
            <h2>{selectedHazard.title ?? '危険地点'}付近</h2>
            <section>
              <h3>危険要因</h3>
              <div className="factor-row">
                {selectedHazard.risk_factors.map((factor) => (
                  <span
                    key={factor}
                    style={{
                      backgroundColor: riskSoftColor(selectedHazard.risk_score),
                      color: riskColor(selectedHazard.risk_score),
                    }}
                  >
                    {factor}
                  </span>
                ))}
              </div>
            </section>
            <section>
              <h3>事故データ</h3>
              <div className="accident-row">
                <Icon name="warning" />
                {selectedHazard.accident_count > 0
                  ? `過去5年間で${selectedHazard.accident_count}件の交通事故`
                  : '過去5年間の事故報告なし'}
              </div>
            </section>
            <section>
              <h3>道路情報</h3>
              <dl className="road-info">
                <div>
                  <dt>道路種別</dt>
                  <dd>{selectedHazard.osm_tags.highway ?? '不明'}</dd>
                </div>
                <div>
                  <dt>歩道</dt>
                  <dd>{selectedHazard.osm_tags.sidewalk ?? '不明'}</dd>
                </div>
              </dl>
            </section>
            <footer>
              <button type="button" onClick={() => setModalId(null)}>
                閉じる
              </button>
              <button className="primary" type="button" onClick={() => setModalId(null)}>
                地図で確認
              </button>
            </footer>
          </article>
        </div>
      )}
    </main>
  )
}

export default App
