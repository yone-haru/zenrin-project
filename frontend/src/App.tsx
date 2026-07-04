import { useEffect, useMemo, useState } from 'react'
import { fetchReports, uploadReport } from './api/reports'
import type { Report } from './api/reports'
import { geocode } from './api/route'
import type { HazardPoint } from './api/route'
import { HazardModal } from './components/HazardModal'
import { HazardPanel } from './components/HazardPanel'
import type { HazardListItem } from './components/HazardPanel'
import { Icon } from './components/Icon'
import { MapView } from './components/MapView'
import { ReportForm } from './components/ReportForm'
import { RouteSummary } from './components/RouteSummary'
import { SearchPanel } from './components/SearchPanel'
import { useGeocode } from './hooks/useGeocode'
import { useRoute } from './hooks/useRoute'
import type { LatLng, Point, SelectedDetail, Target } from './types'
import { formatDistance } from './utils/format'
import { readableRiskText, riskColor } from './utils/riskColor'

function App() {
  const [origin, setOrigin] = useState<Point | null>(null)
  const [destination, setDestination] = useState<Point | null>(null)
  const [originText, setOriginText] = useState('')
  const [destinationText, setDestinationText] = useState('')
  const [pickMode, setPickMode] = useState<Target>('origin')

  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  const [modalDetail, setModalDetail] = useState<SelectedDetail | null>(null)

  const [resolving, setResolving] = useState(false)
  const [resolveError, setResolveError] = useState<string | null>(null)

  const [reports, setReports] = useState<Report[]>([])
  const [isReporting, setIsReporting] = useState(false)
  const [reportDraft, setReportDraft] = useState<LatLng | null>(null)
  const [reportSubmitting, setReportSubmitting] = useState(false)
  const [reportError, setReportError] = useState<string | null>(null)

  const routeState = useRoute()
  const originGeocode = useGeocode(originText, { enabled: !isReporting })
  const destinationGeocode = useGeocode(destinationText, { enabled: !isReporting })

  const isSearching = resolving || routeState.status === 'loading'
  const searchErrorMessage = resolveError ?? routeState.error

  useEffect(() => {
    fetchReports()
      .then(setReports)
      .catch(() => setReports([]))
  }, [])

  const routePositions = useMemo<[number, number][]>(() => {
    if (!routeState.route) return []
    return routeState.route.route_geometry.coordinates.map(([lng, lat]) => [lat, lng])
  }, [routeState.route])

  const mapReports = useMemo(() => {
    const byId = new Map<string, Report>()
    for (const report of reports) byId.set(report.id, report)
    if (routeState.route) {
      for (const { report } of routeState.route.danger_reports) byId.set(report.id, report)
    }
    return Array.from(byId.values())
  }, [reports, routeState.route])

  const selectedHazardId = selectedKey?.startsWith('hazard-') ? selectedKey.slice('hazard-'.length) : null
  const selectedReportId = selectedKey?.startsWith('report-') ? selectedKey.slice('report-'.length) : null

  function openHazard(hazard: HazardPoint) {
    setSelectedKey(`hazard-${hazard.id}`)
    setModalDetail({ kind: 'hazard', hazard })
  }

  function openReport(report: Report, distanceFromRouteM?: number) {
    setSelectedKey(`report-${report.id}`)
    setModalDetail({ kind: 'report', report, distanceFromRouteM })
  }

  const hazardItems: HazardListItem[] = routeState.route
    ? [
        ...routeState.route.hazard_points.map((hazard): HazardListItem => ({
          key: `hazard-${hazard.id}`,
          color: riskColor(hazard.risk_score),
          textColor: readableRiskText(hazard.risk_score),
          scoreLabel: String(hazard.risk_score),
          title: hazard.title ?? '危険地点',
          distanceText:
            hazard.distance_from_origin_m != null
              ? `出発から${formatDistance(hazard.distance_from_origin_m)}`
              : undefined,
          tags: hazard.risk_factors.slice(0, 2),
          sourceLabel: '解析',
          onSelect: () => openHazard(hazard),
        })),
        ...routeState.route.danger_reports.map(({ report, distance_from_route_m }): HazardListItem => ({
          key: `report-${report.id}`,
          color: riskColor(report.risk_score),
          textColor: readableRiskText(report.risk_score),
          scoreLabel: report.risk_score != null ? String(report.risk_score) : '?',
          title: report.description_ai ?? '投稿された危険箇所',
          distanceText: `ルートから${formatDistance(distance_from_route_m)}`,
          tags: report.comment_user ? [report.comment_user.slice(0, 14)] : ['ユーザー投稿'],
          sourceLabel: '投稿',
          onSelect: () => openReport(report, distance_from_route_m),
        })),
      ]
    : []

  async function resolvePoint(text: string, current: Point | null): Promise<Point> {
    const trimmed = text.trim()
    if (!trimmed) {
      throw new Error('出発地と目的地を入力してください')
    }
    if (current && current.address === trimmed) {
      return current
    }
    const results = await geocode(trimmed, 1)
    if (results.length === 0) {
      throw new Error(`「${trimmed}」の地点が見つかりませんでした`)
    }
    return { lat: results[0].lat, lng: results[0].lng, address: results[0].name }
  }

  async function handleSearch() {
    setResolveError(null)
    setResolving(true)
    let resolvedOrigin: Point
    let resolvedDestination: Point
    try {
      ;[resolvedOrigin, resolvedDestination] = await Promise.all([
        resolvePoint(originText, origin),
        resolvePoint(destinationText, destination),
      ])
    } catch (error) {
      setResolving(false)
      setResolveError(error instanceof Error ? error.message : '地点の検索に失敗しました')
      return
    }
    setResolving(false)
    setOrigin(resolvedOrigin)
    setDestination(resolvedDestination)
    setOriginText(resolvedOrigin.address)
    setDestinationText(resolvedDestination.address)

    try {
      const response = await routeState.search(resolvedOrigin, resolvedDestination)
      setSelectedKey(response.hazard_points[0] ? `hazard-${response.hazard_points[0].id}` : null)
      setModalDetail(null)
    } catch {
      // エラーメッセージは routeState.error 経由でバナー表示される
    }
  }

  function handleMapPick(lat: number, lng: number) {
    if (isReporting) {
      setReportDraft({ lat, lng })
      setReportError(null)
      setModalDetail(null)
      return
    }
    const address = `地図指定 ${lat.toFixed(5)}, ${lng.toFixed(5)}`
    const point: Point = { lat, lng, address }
    if (pickMode === 'origin') {
      setOrigin(point)
      setOriginText(address)
      setPickMode('destination')
    } else {
      setDestination(point)
      setDestinationText(address)
      setPickMode('origin')
    }
  }

  function handleSwap() {
    setOrigin(destination)
    setDestination(origin)
    setOriginText(destinationText)
    setDestinationText(originText)
  }

  function handleToggleReporting() {
    setIsReporting((prev) => {
      const next = !prev
      if (!next) {
        setReportDraft(null)
        setReportError(null)
      } else {
        setModalDetail(null)
      }
      return next
    })
  }

  async function handleReportSubmit({ comment, images }: { comment: string; images: File[] }) {
    if (!reportDraft) return
    setReportSubmitting(true)
    setReportError(null)
    try {
      const created = await uploadReport({
        latitude: reportDraft.lat,
        longitude: reportDraft.lng,
        comment,
        images,
      })
      setReports((prev) => [created, ...prev])
      setIsReporting(false)
      setReportDraft(null)
    } catch (error) {
      setReportError(error instanceof Error ? error.message : '投稿に失敗しました')
    } finally {
      setReportSubmitting(false)
    }
  }

  const hintMessage = isReporting
    ? reportDraft
      ? '写真とコメントを入力して送信してください'
      : '地図をクリックして危険箇所の位置を指定してください'
    : routeState.route
      ? 'ルート上の危険箇所を確認できます'
      : `地図をクリックして地点を指定できます（現在: ${pickMode === 'origin' ? '出発地' : '目的地'}を指定中）`

  return (
    <main className="app-shell">
      <MapView
        origin={origin}
        destination={destination}
        routePositions={routePositions}
        hazards={routeState.route?.hazard_points ?? []}
        selectedHazardId={selectedHazardId}
        onSelectHazard={openHazard}
        reports={mapReports}
        selectedReportId={selectedReportId}
        onSelectReport={(report) => openReport(report)}
        reportDraft={reportDraft}
        onMapPick={handleMapPick}
        isSearching={isSearching}
      />

      <SearchPanel
        originText={originText}
        destinationText={destinationText}
        onOriginTextChange={setOriginText}
        onDestinationTextChange={setDestinationText}
        originSuggestions={originGeocode.suggestions}
        destinationSuggestions={destinationGeocode.suggestions}
        originSuggestLoading={originGeocode.loading}
        destinationSuggestLoading={destinationGeocode.loading}
        onSelectOrigin={(result) => {
          setOrigin({ lat: result.lat, lng: result.lng, address: result.name })
          setOriginText(result.name)
          originGeocode.clear()
        }}
        onSelectDestination={(result) => {
          setDestination({ lat: result.lat, lng: result.lng, address: result.name })
          setDestinationText(result.name)
          destinationGeocode.clear()
        }}
        onClearOriginSuggestions={originGeocode.clear}
        onClearDestinationSuggestions={destinationGeocode.clear}
        onSwap={handleSwap}
        onSearch={handleSearch}
        searching={isSearching}
        pickMode={pickMode}
        onSetPickMode={setPickMode}
        isReporting={isReporting}
        onToggleReporting={handleToggleReporting}
      />

      {routeState.route && (
        <RouteSummary
          distanceM={routeState.route.distance_m}
          durationS={routeState.route.duration_s}
          hazardCount={routeState.route.hazard_points.length}
        />
      )}

      {routeState.route && <HazardPanel items={hazardItems} selectedKey={selectedKey} />}

      {!searchErrorMessage && <div className={`hint-pill ${isReporting ? 'is-reporting' : ''}`}>
        <Icon name={isReporting ? 'camera' : 'pin'} />
        {hintMessage}
      </div>}

      {searchErrorMessage && (
        <div className="error-banner" role="alert">
          <Icon name="warning" />
          <span>{searchErrorMessage}</span>
          <button type="button" onClick={handleSearch} disabled={isSearching}>
            <Icon name="refresh" />
            再試行
          </button>
        </div>
      )}

      {modalDetail && (
        <HazardModal
          detail={modalDetail}
          onClose={() => setModalDetail(null)}
          onLocate={() => setModalDetail(null)}
        />
      )}

      {isReporting && reportDraft && (
        <ReportForm
          position={reportDraft}
          submitting={reportSubmitting}
          error={reportError}
          onCancel={() => {
            setReportDraft(null)
            setReportError(null)
          }}
          onSubmit={handleReportSubmit}
        />
      )}
    </main>
  )
}

export default App
