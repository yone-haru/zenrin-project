import type { RouteOption } from '../api/route'
import { formatDistance, formatDuration } from '../utils/format'
import { rankForSafetyScore } from '../utils/grade'
import { Icon } from './Icon'
import { HazardList } from './HazardPanel'
import type { HazardListItem } from './HazardPanel'
import { RouteCards } from './RouteCards'

interface BottomSheetProps {
  routes: RouteOption[]
  selectedRoute: RouteOption
  selectedRouteId: string
  onSelectRoute: (routeId: string) => void
  hazardItems: HazardListItem[]
  selectedKey: string | null
  onShare: () => void
  expanded: boolean
  onToggleExpanded: () => void
}

/**
 * 検索後に地図下部へ現れるボトムシート。peek(サマリーのみ)⇔expanded(ルート比較+危険箇所一覧)を
 * ハンドルのタップで切り替える（plan v3.1・ドラッグ実装は不要）。
 */
export function BottomSheet({
  routes,
  selectedRoute,
  selectedRouteId,
  onSelectRoute,
  hazardItems,
  selectedKey,
  onShare,
  expanded,
  onToggleExpanded,
}: BottomSheetProps) {
  const rank = rankForSafetyScore(selectedRoute.safety_score)

  return (
    <section className={`bottom-sheet ${expanded ? 'is-expanded' : 'is-peek'}`} aria-label="ルート概要">
      <button
        type="button"
        className="sheet-toggle"
        onClick={onToggleExpanded}
        aria-expanded={expanded}
        aria-label={expanded ? 'ルート概要を折りたたむ' : 'ルート概要を詳しく表示'}
      >
        <span className="sheet-handle-bar" aria-hidden="true" />
        <div className="sheet-peek-row">
          <span className="rank-badge" style={{ backgroundColor: `${rank.color}1a`, color: rank.color }}>
            {rank.label}
          </span>
          <div className="sheet-peek-main">
            <strong className="sheet-duration">{formatDuration(selectedRoute.duration_s)}</strong>
            <span className="sheet-meta">
              {formatDistance(selectedRoute.distance_m)} ・ 危険 {selectedRoute.hazard_points.length}件 ・ 危険度{' '}
              {rank.danger}
            </span>
          </div>
          <Icon name="chevronDown" />
        </div>
      </button>
      <button
        type="button"
        className="share-button sheet-share"
        onClick={(event) => {
          event.stopPropagation()
          onShare()
        }}
      >
        <Icon name="share" />
        共有
      </button>

      {expanded && (
        <div className="sheet-expanded-content">
          <RouteCards routes={routes} selectedRouteId={selectedRouteId} onSelect={onSelectRoute} />
          <div className="sheet-hazard-section">
            <div className="sheet-hazard-title">
              <h2>危険箇所一覧</h2>
              <span className="panel-count">{hazardItems.length}件</span>
            </div>
            <HazardList items={hazardItems} selectedKey={selectedKey} />
          </div>
        </div>
      )}
    </section>
  )
}

/** ルート検索中に表示するボトムシート形のスケルトン。 */
export function BottomSheetSkeleton() {
  return (
    <section className="bottom-sheet is-peek bottom-sheet-skeleton" aria-hidden="true">
      <div className="sheet-toggle">
        <span className="sheet-handle-bar" aria-hidden="true" />
        <div className="sheet-peek-row">
          <div className="skeleton-block skeleton-badge" />
          <div className="sheet-peek-main">
            <div className="skeleton-block skeleton-line" />
            <div className="skeleton-block skeleton-line short" />
          </div>
        </div>
      </div>
    </section>
  )
}
