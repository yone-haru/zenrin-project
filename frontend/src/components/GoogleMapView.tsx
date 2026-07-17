import { AdvancedMarker, APIProvider, Map, useMap } from '@vis.gl/react-google-maps'
import type { MapMouseEvent } from '@vis.gl/react-google-maps'
import type { CSSProperties } from 'react'
import { useEffect, useMemo } from 'react'
import type { HazardPoint, RouteOption } from '../api/route'
import type { Report } from '../api/reports'
import { colorForRiskScore, readableRiskText, riskColor } from '../utils/riskColor'
import type { MapViewProps } from './mapTypes'

const NAGASAKI_CENTER = { lat: 32.7503, lng: 129.8777 }
const MAP_ID = 'SAFETY_MAP'

// fitBounds時、UIオーバーレイを避けるパディング。MapView.tsx(Leaflet版)のFIT_PADDING_*と同じ値（plan v3.1/v3.2）。
const FIT_PADDING_DESKTOP: google.maps.Padding = { top: 90, left: 460, bottom: 80, right: 60 }
const FIT_PADDING_MOBILE: google.maps.Padding = { top: 150, left: 24, bottom: 240, right: 24 }

/** CSSカスタムプロパティ(--risk-color等)を型エラーなく渡すためのstyle型。 */
type CSSVars = CSSProperties & Record<`--${string}`, string | number>

/** RouteOptionのGeoJSON座標([lng,lat])をGoogle Maps座標へ変換する。 */
function toPath(route: RouteOption): google.maps.LatLngLiteral[] {
  return route.route_geometry.coordinates.map(([lng, lat]) => ({ lat, lng }))
}

/**
 * ルート線1本を「カジング＋上層」の2枚のgoogle.maps.Polylineとして描画するコンポーネント。
 * react-leaflet版(MapView.tsx)と同じ視覚仕様（plan v3.2）。
 * useMap()+useEffectでPolylineインスタンスを直接生成し、アンマウント/props変化時に破棄する。
 */
function RoutePolylinePair({
  path,
  casingColor,
  casingWeight,
  topColor,
  topWeight,
  zIndexBase,
  clickable,
  onClick,
}: {
  path: google.maps.LatLngLiteral[]
  casingColor: string
  casingWeight: number
  topColor: string
  topWeight: number
  zIndexBase: number
  clickable: boolean
  onClick?: () => void
}) {
  const map = useMap()

  useEffect(() => {
    if (!map || path.length < 2) return undefined

    const casing = new google.maps.Polyline({
      path,
      strokeColor: casingColor,
      strokeWeight: casingWeight,
      strokeOpacity: 1,
      zIndex: zIndexBase,
      clickable,
      map,
    })
    const top = new google.maps.Polyline({
      path,
      strokeColor: topColor,
      strokeWeight: topWeight,
      strokeOpacity: 1,
      zIndex: zIndexBase + 1,
      clickable,
      map,
    })

    const listeners: google.maps.MapsEventListener[] = []
    if (onClick) {
      listeners.push(casing.addListener('click', onClick))
      listeners.push(top.addListener('click', onClick))
    }

    return () => {
      for (const listener of listeners) listener.remove()
      casing.setMap(null)
      top.setMap(null)
    }
  }, [map, path, casingColor, casingWeight, topColor, topWeight, zIndexBase, clickable, onClick])

  return null
}

/** 選択ルート変更時にレスポンシブpaddingでfitBoundsする（plan v3.1と同じ挙動）。 */
function FitRouteBounds({ path }: { path: google.maps.LatLngLiteral[] }) {
  const map = useMap()

  useEffect(() => {
    if (!map || path.length < 2) return
    const bounds = new google.maps.LatLngBounds()
    for (const point of path) bounds.extend(point)
    const padding = window.innerWidth >= 768 ? FIT_PADDING_DESKTOP : FIT_PADDING_MOBILE
    map.fitBounds(bounds, padding)
  }, [map, path])

  return null
}

function OriginMarkerContent() {
  return <div className="origin-marker" />
}

function DestinationMarkerContent() {
  return (
    <div className="destination-marker">
      <svg viewBox="0 0 24 36" aria-hidden="true">
        <path d="M12 0C5.4 0 0 5.4 0 12c0 9 12 24 12 24s12-15 12-24c0-6.6-5.4-12-12-12z" fill="#ea4335" />
        <circle cx="12" cy="12" r="5" fill="#ffffff" />
      </svg>
    </div>
  )
}

/** 危険ピンのデクラッタ（plan v3.1）: score2=10pxドット/3=14pxドット/4-5=24px数字バッジ。選択中は拡大。 */
function HazardMarkerContent({ hazard, selected }: { hazard: HazardPoint; selected: boolean }) {
  const score = hazard.risk_score
  const color = riskColor(score)

  if (score <= 3) {
    const size = selected ? (score <= 2 ? 13 : 18) : score <= 2 ? 10 : 14
    const style: CSSVars = { width: size, height: size, '--risk-color': color }
    return <div className={`hazard-dot ${selected ? 'is-selected' : ''}`} style={style} />
  }

  const size = selected ? 31 : 24
  const style: CSSVars = {
    width: size,
    height: size,
    '--risk-color': color,
    '--risk-text': readableRiskText(score),
  }
  return (
    <div className={`hazard-badge ${selected ? 'is-selected' : ''}`} style={style}>
      {score}
    </div>
  )
}

function ReportMarkerContent({ report, selected }: { report: Report; selected: boolean }) {
  const color = colorForRiskScore(report.risk_score)
  const style: CSSVars = { '--report-color': color }
  return (
    <div className={`report-marker ${selected ? 'is-selected' : ''}`} style={style}>
      <svg aria-hidden="true" viewBox="0 0 24 24">
        <path d="M4 8h3l1.7-2.2A1 1 0 0 1 9.5 5h5a1 1 0 0 1 .8.4L17 8h3a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1zm8 3a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7z" />
      </svg>
    </div>
  )
}

function ReportDraftMarkerContent() {
  return (
    <div className="report-draft-marker">
      <svg aria-hidden="true" viewBox="0 0 24 24">
        <path d="M4 8h3l1.7-2.2A1 1 0 0 1 9.5 5h5a1 1 0 0 1 .8.4L17 8h3a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1zm8 3a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7z" />
      </svg>
    </div>
  )
}

interface GoogleMapViewProps extends MapViewProps {
  /** Maps JavaScript API を有効化したGoogle Cloudのキー。空文字では呼び出し元がこのコンポーネントを使わない想定。 */
  apiKey: string
}

export function GoogleMapView({
  apiKey,
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
}: GoogleMapViewProps) {
  const selectedRoute = routes.find((route) => route.id === selectedRouteId) ?? routes[0] ?? null
  const alternativeRoutes = routes.filter((route) => route.id !== selectedRoute?.id)
  const selectedPath = useMemo(() => (selectedRoute ? toPath(selectedRoute) : []), [selectedRoute])

  function handleMapClick(event: MapMouseEvent) {
    const latLng = event.detail.latLng
    if (latLng) onMapPick(latLng.lat, latLng.lng)
  }

  return (
    <div className="map-wrapper">
      <APIProvider apiKey={apiKey} libraries={['marker']}>
        <Map
          mapId={MAP_ID}
          className="safety-map"
          defaultCenter={NAGASAKI_CENTER}
          defaultZoom={14}
          disableDefaultUI
          gestureHandling="greedy"
          onClick={handleMapClick}
          onContextmenu={handleMapClick}
        >
          {selectedPath.length > 1 && <FitRouteBounds path={selectedPath} />}

          {alternativeRoutes.map((route) => (
            <RoutePolylinePair
              key={route.id}
              path={toPath(route)}
              casingColor="#9aa0a6"
              casingWeight={7}
              topColor="#d2d5d9"
              topWeight={4}
              zIndexBase={1}
              clickable
              onClick={() => onSelectRoute(route.id)}
            />
          ))}

          {selectedPath.length > 1 && (
            <RoutePolylinePair
              path={selectedPath}
              casingColor="#1557b0"
              casingWeight={9}
              topColor="#4285f4"
              topWeight={6}
              zIndexBase={10}
              clickable={false}
            />
          )}

          {origin && (
            <AdvancedMarker position={{ lat: origin.lat, lng: origin.lng }} anchorLeft="-50%" anchorTop="-50%">
              <OriginMarkerContent />
            </AdvancedMarker>
          )}

          {destination && (
            <AdvancedMarker position={{ lat: destination.lat, lng: destination.lng }}>
              <DestinationMarkerContent />
            </AdvancedMarker>
          )}

          {hazards.map((hazard) => {
            const selected = hazard.id === selectedHazardId
            return (
              <AdvancedMarker
                key={hazard.id}
                position={{ lat: hazard.latitude, lng: hazard.longitude }}
                anchorLeft="-50%"
                anchorTop="-50%"
                zIndex={selected ? 50 : 20}
                onClick={() => onSelectHazard(hazard)}
              >
                <HazardMarkerContent hazard={hazard} selected={selected} />
              </AdvancedMarker>
            )
          })}

          {reports.map((report) => {
            const selected = report.id === selectedReportId
            return (
              <AdvancedMarker
                key={report.id}
                position={{ lat: report.latitude, lng: report.longitude }}
                anchorLeft="-50%"
                anchorTop="-50%"
                zIndex={selected ? 51 : 21}
                onClick={() => onSelectReport(report)}
              >
                <ReportMarkerContent report={report} selected={selected} />
              </AdvancedMarker>
            )
          })}

          {reportDraft && (
            <AdvancedMarker
              position={{ lat: reportDraft.lat, lng: reportDraft.lng }}
              anchorLeft="-50%"
              anchorTop="-50%"
              clickable={false}
              zIndex={60}
            >
              <ReportDraftMarkerContent />
            </AdvancedMarker>
          )}
        </Map>
      </APIProvider>
      {isSearching && (
        <div className="map-loading-overlay" role="status" aria-live="polite">
          <span className="spinner" aria-hidden="true" />
          ルートを検索しています
        </div>
      )}
    </div>
  )
}
