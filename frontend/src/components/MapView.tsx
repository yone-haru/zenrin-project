import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { useEffect } from 'react'
import { MapContainer, Marker, Polyline, TileLayer, useMap, useMapEvents } from 'react-leaflet'
import type { HazardPoint } from '../api/route'
import type { Report } from '../api/reports'
import type { LatLng, Point } from '../types'
import { colorForRiskScore, readableRiskText, riskColor } from '../utils/riskColor'

const NAGASAKI_CENTER: [number, number] = [32.7503, 129.8777]
const LONG_PRESS_MS = 600
const LONG_PRESS_MOVE_TOLERANCE_PX = 12

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

function computeRouteCues(routePositions: [number, number][]) {
  if (routePositions.length < 3) return []
  const cueCount = Math.min(5, routePositions.length - 2)
  return Array.from({ length: cueCount }, (_, index) => {
    const pointIndex = Math.max(1, Math.round(((index + 1) * (routePositions.length - 1)) / (cueCount + 1)))
    return {
      position: routePositions[pointIndex],
      angle: bearing(routePositions[pointIndex - 1], routePositions[Math.min(routePositions.length - 1, pointIndex + 1)]),
    }
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
      map.fitBounds(points, { paddingTopLeft: [390, 40], paddingBottomRight: [360, 40] })
    }
  }, [map, points])
  return null
}

interface MapViewProps {
  origin: Point | null
  destination: Point | null
  routePositions: [number, number][]
  hazards: HazardPoint[]
  selectedHazardId: string | null
  onSelectHazard: (hazard: HazardPoint) => void
  reports: Report[]
  selectedReportId: string | null
  onSelectReport: (report: Report) => void
  reportDraft: LatLng | null
  onMapPick: (lat: number, lng: number) => void
  isSearching: boolean
}

export function MapView({
  origin,
  destination,
  routePositions,
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
  const routeCues = computeRouteCues(routePositions)
  const routeLabelPosition = routePositions[Math.floor(routePositions.length / 2)]

  return (
    <div className="map-wrapper">
      <MapContainer center={NAGASAKI_CENTER} zoom={14} className="safety-map" zoomControl={false}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <MapClickHandler onPick={onMapPick} />
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
