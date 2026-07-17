import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { Fragment, useEffect } from 'react'
import { MapContainer, Marker, Polyline, TileLayer, useMap, useMapEvents } from 'react-leaflet'
import type { HazardPoint, RouteOption } from '../api/route'
import type { Report } from '../api/reports'
import { colorForRiskScore, readableRiskText, riskColor } from '../utils/riskColor'
import type { MapViewProps } from './mapTypes'

const NAGASAKI_CENTER: [number, number] = [32.7503, 129.8777]
const LONG_PRESS_MS = 600
const LONG_PRESS_MOVE_TOLERANCE_PX = 12

// fitBounds時、UIオーバーレイを避けるパディング（plan v3.1）。
// デスクトップは検索カード・ボトムシートが左寄せ(幅~420px)なので左を大きく空け、
// モバイルは全幅ボトムシートの分だけ下を空ける。
const FIT_PADDING_DESKTOP = {
  paddingTopLeft: [460, 90] as [number, number],
  paddingBottomRight: [60, 80] as [number, number],
}
const FIT_PADDING_MOBILE = {
  paddingTopLeft: [24, 150] as [number, number],
  paddingBottomRight: [24, 240] as [number, number],
}

function originIcon() {
  return L.divIcon({
    className: '',
    iconSize: [20, 20],
    iconAnchor: [10, 10],
    html: '<div class="origin-marker"></div>',
  })
}

function destinationIcon() {
  return L.divIcon({
    className: '',
    iconSize: [30, 42],
    iconAnchor: [15, 40],
    html: '<div class="destination-marker"><svg viewBox="0 0 24 36" aria-hidden="true"><path d="M12 0C5.4 0 0 5.4 0 12c0 9 12 24 12 24s12-15 12-24c0-6.6-5.4-12-12-12z" fill="#ea4335"/><circle cx="12" cy="12" r="5" fill="#ffffff"/></svg></div>',
  })
}

/** 危険ピンのデクラッタ（plan v3.1）: score2=10pxドット/3=14pxドット/4-5=24px数字バッジ。選択中は1.3倍+リング。 */
function hazardIcon(hazard: HazardPoint, selected: boolean) {
  const score = hazard.risk_score
  const color = riskColor(score)

  if (score <= 2) {
    const size = selected ? 13 : 10
    return L.divIcon({
      className: '',
      iconSize: [size, size],
      iconAnchor: [size / 2, size / 2],
      html: `<div class="hazard-dot ${selected ? 'is-selected' : ''}" style="--risk-color:${color}"></div>`,
    })
  }

  if (score === 3) {
    const size = selected ? 18 : 14
    return L.divIcon({
      className: '',
      iconSize: [size, size],
      iconAnchor: [size / 2, size / 2],
      html: `<div class="hazard-dot ${selected ? 'is-selected' : ''}" style="--risk-color:${color}"></div>`,
    })
  }

  const size = selected ? 31 : 24
  return L.divIcon({
    className: '',
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    html: `<div class="hazard-badge ${selected ? 'is-selected' : ''}" style="--risk-color:${color};--risk-text:${readableRiskText(score)}">${score}</div>`,
  })
}

function reportIcon(report: Report, selected: boolean) {
  const color = colorForRiskScore(report.risk_score)
  return L.divIcon({
    className: '',
    iconSize: selected ? [34, 34] : [28, 28],
    iconAnchor: selected ? [17, 17] : [14, 14],
    html: `<div class="report-marker ${selected ? 'is-selected' : ''}" style="--report-color:${color}"><svg aria-hidden="true" viewBox="0 0 24 24"><path d="M4 8h3l1.7-2.2A1 1 0 0 1 9.5 5h5a1 1 0 0 1 .8.4L17 8h3a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1zm8 3a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7z"/></svg></div>`,
  })
}

function reportDraftIcon() {
  return L.divIcon({
    className: '',
    iconSize: [40, 40],
    iconAnchor: [20, 20],
    html: '<div class="report-draft-marker"><svg aria-hidden="true" viewBox="0 0 24 24"><path d="M4 8h3l1.7-2.2A1 1 0 0 1 9.5 5h5a1 1 0 0 1 .8.4L17 8h3a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1zm8 3a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7z"/></svg></div>',
  })
}

/** クリック・右クリック・長押し(タッチ)のいずれでも地点指定できるようにする。 */
function MapClickHandler({ onPick }: { onPick: (lat: number, lng: number) => void }) {
  const map = useMap()

  useMapEvents({
    click(event) {
      onPick(event.latlng.lat, event.latlng.lng)
    },
    contextmenu(event) {
      event.originalEvent.preventDefault()
      onPick(event.latlng.lat, event.latlng.lng)
    },
  })

  useEffect(() => {
    const container = map.getContainer()
    let timer: ReturnType<typeof setTimeout> | null = null
    let startPoint: { x: number; y: number } | null = null

    function clear() {
      if (timer) {
        clearTimeout(timer)
        timer = null
      }
      startPoint = null
    }

    function handleTouchStart(event: TouchEvent) {
      if (event.touches.length !== 1) return
      const touch = event.touches[0]
      startPoint = { x: touch.clientX, y: touch.clientY }
      timer = setTimeout(() => {
        const rect = container.getBoundingClientRect()
        const point = L.point(touch.clientX - rect.left, touch.clientY - rect.top)
        const latlng = map.containerPointToLatLng(point)
        onPick(latlng.lat, latlng.lng)
      }, LONG_PRESS_MS)
    }

    function handleTouchMove(event: TouchEvent) {
      if (!startPoint || event.touches.length !== 1) return
      const touch = event.touches[0]
      const dx = touch.clientX - startPoint.x
      const dy = touch.clientY - startPoint.y
      if (Math.hypot(dx, dy) > LONG_PRESS_MOVE_TOLERANCE_PX) clear()
    }

    container.addEventListener('touchstart', handleTouchStart, { passive: true })
    container.addEventListener('touchmove', handleTouchMove, { passive: true })
    container.addEventListener('touchend', clear)
    container.addEventListener('touchcancel', clear)

    return () => {
      clear()
      container.removeEventListener('touchstart', handleTouchStart)
      container.removeEventListener('touchmove', handleTouchMove)
      container.removeEventListener('touchend', clear)
      container.removeEventListener('touchcancel', clear)
    }
  }, [map, onPick])

  return null
}

function FitRoute({ points }: { points: [number, number][] }) {
  const map = useMap()
  useEffect(() => {
    if (points.length > 1) {
      const padding = window.innerWidth >= 768 ? FIT_PADDING_DESKTOP : FIT_PADDING_MOBILE
      map.fitBounds(points, padding)
    }
  }, [map, points])
  return null
}

/** RouteOptionのGeoJSON座標([lng,lat])をLeaflet座標([lat,lng])へ変換する。 */
function toPositions(route: RouteOption): [number, number][] {
  return route.route_geometry.coordinates.map(([lng, lat]) => [lat, lng])
}

export function MapView({
  origin,
  destination,
  routes,
  selectedRouteId,
  onSelectRoute,
  hazards,
  selectedHazardId,
  onSelectHazard,
  reports,
  selectedReportId,
  onSelectReport,
  reportDraft,
  onMapPick,
  isSearching,
}: MapViewProps) {
  const selectedRoute = routes.find((route) => route.id === selectedRouteId) ?? routes[0] ?? null
  const selectedPositions = selectedRoute ? toPositions(selectedRoute) : []
  const alternativeRoutes = routes.filter((route) => route.id !== selectedRoute?.id)

  return (
    <div className="map-wrapper">
      <MapContainer center={NAGASAKI_CENTER} zoom={14} className="safety-map" zoomControl={false}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
          subdomains="abcd"
          maxZoom={20}
          detectRetina
        />
        <MapClickHandler onPick={onMapPick} />
        {selectedPositions.length > 0 && <FitRoute points={selectedPositions} />}
        {alternativeRoutes.map((route) => {
          const positions = toPositions(route)
          return (
            <Fragment key={route.id}>
              <Polyline
                positions={positions}
                pathOptions={{
                  color: '#9aa0a6',
                  weight: 7,
                  opacity: 0.9,
                  lineCap: 'round',
                  lineJoin: 'round',
                }}
                eventHandlers={{ click: () => onSelectRoute(route.id) }}
              />
              <Polyline
                positions={positions}
                pathOptions={{
                  color: '#d2d5d9',
                  weight: 4,
                  opacity: 0.95,
                  lineCap: 'round',
                  lineJoin: 'round',
                }}
                eventHandlers={{ click: () => onSelectRoute(route.id) }}
              />
            </Fragment>
          )
        })}
        {selectedPositions.length > 0 && (
          <>
            <Polyline
              positions={selectedPositions}
              pathOptions={{ color: '#1557b0', weight: 9, opacity: 1, lineCap: 'round', lineJoin: 'round' }}
            />
            <Polyline
              positions={selectedPositions}
              pathOptions={{ color: '#4285f4', weight: 6, opacity: 1, lineCap: 'round', lineJoin: 'round' }}
            />
          </>
        )}
        {origin && <Marker position={[origin.lat, origin.lng]} icon={originIcon()} />}
        {destination && <Marker position={[destination.lat, destination.lng]} icon={destinationIcon()} />}
        {hazards.map((hazard) => (
          <Marker
            key={hazard.id}
            position={[hazard.latitude, hazard.longitude]}
            icon={hazardIcon(hazard, hazard.id === selectedHazardId)}
            eventHandlers={{ click: () => onSelectHazard(hazard) }}
          />
        ))}
        {reports.map((report) => (
          <Marker
            key={report.id}
            position={[report.latitude, report.longitude]}
            icon={reportIcon(report, report.id === selectedReportId)}
            eventHandlers={{ click: () => onSelectReport(report) }}
          />
        ))}
        {reportDraft && <Marker position={[reportDraft.lat, reportDraft.lng]} icon={reportDraftIcon()} interactive={false} />}
      </MapContainer>
      {isSearching && (
        <div className="map-loading-overlay" role="status" aria-live="polite">
          <span className="spinner" aria-hidden="true" />
          ルートを検索しています
        </div>
      )}
    </div>
  )
}
