import { useEffect, useMemo, useState } from 'react'
import { fetchReports, uploadReport } from './api/reports'
import type { Report } from './api/reports'
import { geocode } from './api/route'
import type { HazardPoint } from './api/route'
import { AdminPanel } from './components/AdminPanel'
import { BottomSheet, BottomSheetSkeleton } from './components/BottomSheet'
import { EmptyStateCard } from './components/EmptyStateCard'
import { GoogleMapView } from './components/GoogleMapView'
import { HazardModal } from './components/HazardModal'
import type { HazardListItem } from './components/HazardPanel'
import { Icon } from './components/Icon'
import { MapView } from './components/MapView'
import type { MapViewProps } from './components/mapTypes'
import { ReportForm } from './components/ReportForm'
import { SearchPanel } from './components/SearchPanel'
import { useGeocode } from './hooks/useGeocode'
import { useRoute } from './hooks/useRoute'
import type { LatLng, Point, SelectedDetail, Target } from './types'
import { formatDistance, formatDuration } from './utils/format'
import { readableRiskText, riskColor } from './utils/riskColor'

const TOAST_DURATION_MS = 3200

function readAdminModeFromUrl(): boolean {
  return new URLSearchParams(window.location.search).get('admin') === '1'
}

// キー未設定時は現行のLeaflet版(MapView)にフォールバックする（plan v3.2）。
const googleMapsApiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY ?? ''

function App() {
  const [origin, setOrigin] = useState<Point | null>(null)
  const [destination, setDestination] = useState<Point | null>(null)
  const [originText, setOriginText] = useState('')
  const [destinationText, setDestinationText] = useState('')
  const [pickMode, setPickMode] = useState<Target>('origin')

  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null)
  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  const [modalDetail, setModalDetail] = useState<SelectedDetail | null>(null)
  const [sheetExpanded, setSheetExpanded] = useState(true)

  const [resolving, setResolving] = useState(false)
  const [resolveError, setResolveError] = useState<string | null>(null)

  const [reports, setReports] = useState<Report[]>([])
  const [isReporting, setIsReporting] = useState(false)
  const [reportDraft, setReportDraft] = useState<LatLng | null>(null)
  const [reportSubmitting, setReportSubmitting] = useState(false)
  const [reportError, setReportError] = useState<string | null>(null)

  const [locatingCurrentLocation, setLocatingCurrentLocation] = useState(false)
  const [currentLocationError, setCurrentLocationError] = useState<string | null>(null)

  const [toastMessage, setToastMessage] = useState<string | null>(null)

  const [isAdminMode] = useState(readAdminModeFromUrl)
  const [showAdminPanel, setShowAdminPanel] = useState(false)

  const routeState = useRoute()
  // 確定済みの地点と同じテキストのときはサジェストを出さない（検索・候補選択の直後に開き直るのを防ぐ）
  const originGeocode = useGeocode(originText, {
    enabled: !isReporting && originText.trim() !== (origin?.address ?? ''),
  })
  const destinationGeocode = useGeocode(destinationText, {
    enabled: !isReporting && destinationText.trim() !== (destination?.address ?? ''),
  })

  const isSearching = resolving || routeState.status === 'loading'
  const searchErrorMessage = resolveError ?? routeState.error

  const routes = routeState.routes
  const selectedRoute = routes.find((route) => route.id === selectedRouteId) ?? routes[0] ?? null

  useEffect(() => {
    fetchReports()
      .then(setReports)
      .catch(() => setReports([]))
  }, [])

  const mapReports = useMemo(() => {
    const byId = new Map<string, Report>()
    for (const report of reports) byId.set(report.id, report)
    if (selectedRoute) {
      for (const { report } of selectedRoute.danger_reports) byId.set(report.id, report)
    }
    return Array.from(byId.values())
  }, [reports, selectedRoute])

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

  const hazardItems: HazardListItem[] = selectedRoute
    ? [
        ...selectedRoute.hazard_points.map((hazard): HazardListItem => ({
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
        ...selectedRoute.danger_reports.map(({ report, distance_from_route_m }): HazardListItem => ({
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

  function showToast(message: string) {
    setToastMessage(message)
    window.setTimeout(() => setToastMessage(null), TOAST_DURATION_MS)
  }

  async function performSearch(originQuery: string, destinationQuery: string) {
    setResolveError(null)
    setResolving(true)
    let resolvedOrigin: Point
    let resolvedDestination: Point
    try {
      ;[resolvedOrigin, resolvedDestination] = await Promise.all([
        resolvePoint(originQuery, origin),
        resolvePoint(destinationQuery, destination),
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
      const firstRoute = response.routes[0] ?? null
      setSelectedRouteId(firstRoute?.id ?? null)
      setSelectedKey(firstRoute?.hazard_points[0] ? `hazard-${firstRoute.hazard_points[0].id}` : null)
      setModalDetail(null)
      setSheetExpanded(true)

      const params = new URLSearchParams({ from: resolvedOrigin.address, to: resolvedDestination.address })
      window.history.replaceState(null, '', `?${params.toString()}`)
    } catch {
      // エラーメッセージは routeState.error 経由でバナー表示される
    }
  }

  async function handleSearch() {
    await performSearch(originText, destinationText)
  }

  // 共有URL(?from=&to=)からの初回自動検索。effect本体で直接setStateしない
  // （eslint-plugin-react-hooks の set-state-in-effect 対策。CLAUDE.mdのハマりどころ参照）。
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const from = params.get('from')
    const to = params.get('to')
    if (!from || !to) return
    const timer = window.setTimeout(() => {
      setOriginText(from)
      setDestinationText(to)
      void performSearch(from, to)
    }, 0)
    return () => window.clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps -- マウント時に共有URLを一度だけ適用する
  }, [])

  function handleSelectRoute(routeId: string) {
    setSelectedRouteId(routeId)
    setSelectedKey(null)
    setModalDetail(null)
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

  function handleUseCurrentLocation() {
    if (!navigator.geolocation) {
      setCurrentLocationError('この端末では現在地を利用できません')
      return
    }
    setCurrentLocationError(null)
    setLocatingCurrentLocation(true)
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const point: Point = { lat: position.coords.latitude, lng: position.coords.longitude, address: '現在地' }
        setOrigin(point)
        setOriginText('現在地')
        setLocatingCurrentLocation(false)
      },
      (error) => {
        setLocatingCurrentLocation(false)
        setCurrentLocationError(
          error.code === error.PERMISSION_DENIED
            ? '現在地の利用が許可されていません'
            : '現在地を取得できませんでした',
        )
      },
      { enableHighAccuracy: true, timeout: 10000 },
    )
  }

  function buildShareUrl(): string {
    const params = new URLSearchParams()
    if (originText.trim()) params.set('from', originText.trim())
    if (destinationText.trim()) params.set('to', destinationText.trim())
    const query = params.toString()
    return `${window.location.origin}${window.location.pathname}${query ? `?${query}` : ''}`
  }

  function handleShare() {
    const url = buildShareUrl()
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(url).then(
        () => showToast('リンクをコピーしました'),
        () => showToast(url),
      )
    } else {
      showToast(url)
    }
  }

  const hintMessage = isReporting
    ? reportDraft
      ? '写真とコメントを入力して送信してください'
      : '地図をクリックして危険箇所の位置を指定してください'
    : selectedRoute
      ? 'ルート上の危険箇所を確認できます'
      : `地図をクリックして地点を指定できます（現在: ${pickMode === 'origin' ? '出発地' : '目的地'}を指定中）`

  // ルートが選択済みの通常時はボトムシートが情報を担うため、ヒントピルは
  // 報告モード中か、まだルート未選択のときだけ表示する（重なり回避）。
  const showHintPill = !searchErrorMessage && (isReporting || !selectedRoute)
  const sheetVisible = !isSearching && !!selectedRoute

  const mapViewProps: MapViewProps = {
    origin,
    destination,
    routes,
    selectedRouteId: selectedRoute?.id ?? null,
    onSelectRoute: handleSelectRoute,
    hazards: selectedRoute?.hazard_points ?? [],
    selectedHazardId,
    onSelectHazard: openHazard,
    reports: mapReports,
    selectedReportId,
    onSelectReport: (report) => openReport(report),
    reportDraft,
    onMapPick: handleMapPick,
    isSearching,
  }

  return (
    <main className="app-shell">
      {googleMapsApiKey ? (
        <GoogleMapView apiKey={googleMapsApiKey} {...mapViewProps} />
      ) : (
        <MapView {...mapViewProps} />
      )}

      <div className="top-stack">
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
          onUseCurrentLocation={handleUseCurrentLocation}
          locatingCurrentLocation={locatingCurrentLocation}
          currentLocationError={currentLocationError}
        />

        {!isSearching && routes.length === 0 && !searchErrorMessage && <EmptyStateCard />}
      </div>

      {isSearching && <BottomSheetSkeleton />}

      {sheetVisible && selectedRoute && (
        <BottomSheet
          routes={routes}
          selectedRoute={selectedRoute}
          selectedRouteId={selectedRoute.id}
          onSelectRoute={handleSelectRoute}
          hazardItems={hazardItems}
          selectedKey={selectedKey}
          onShare={handleShare}
          expanded={sheetExpanded}
          onToggleExpanded={() => setSheetExpanded((value) => !value)}
        />
      )}

      <div className={`fab-stack ${sheetVisible ? 'above-sheet' : ''}`}>
        {isAdminMode && (
          <button
            type="button"
            className="fab fab-admin"
            onClick={() => setShowAdminPanel(true)}
            aria-label="管理パネルを開く"
          >
            <Icon name="lock" />
          </button>
        )}
        <button
          type="button"
          className={`fab fab-report ${isReporting ? 'is-active' : ''}`}
          aria-pressed={isReporting}
          aria-label={isReporting ? '危険箇所の報告をやめる' : '危険箇所を報告する'}
          onClick={handleToggleReporting}
        >
          <Icon name={isReporting ? 'close' : 'camera'} />
        </button>
      </div>

      {showHintPill && (
        <div className={`hint-pill ${isReporting ? 'is-reporting' : ''} ${selectedRoute ? 'above-sheet' : ''}`}>
          <Icon name={isReporting ? 'camera' : 'pin'} />
          {hintMessage}
        </div>
      )}

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

      {toastMessage && (
        <div className="toast" role="status">
          {toastMessage}
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

      {showAdminPanel && (
        <AdminPanel
          reports={reports}
          onUpdateReport={(updated) => setReports((prev) => prev.map((r) => (r.id === updated.id ? updated : r)))}
          onClose={() => setShowAdminPanel(false)}
        />
      )}

      {selectedRoute && (
        <section className="print-only">
          <h1>通学路あんぜんマップ - ルート概要</h1>
          <p>出発地: {origin?.address ?? originText}</p>
          <p>目的地: {destination?.address ?? destinationText}</p>
          <p>
            安全グレード: {selectedRoute.safety_grade}（安全スコア {selectedRoute.safety_score}）
          </p>
          <p>
            距離: {formatDistance(selectedRoute.distance_m)} / 所要時間: {formatDuration(selectedRoute.duration_s)}
          </p>
          <h2>危険箇所一覧</h2>
          <ol>
            {hazardItems.map((item) => (
              <li key={item.key}>
                {item.title}（危険度 {item.scoreLabel}）{item.distanceText ? ` ${item.distanceText}` : ''}
              </li>
            ))}
          </ol>
        </section>
      )}
    </main>
  )
}

export default App
