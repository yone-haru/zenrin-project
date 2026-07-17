import type { RouteOption } from '../api/route'
import { formatDistance, formatDuration } from '../utils/format'
import { GRADE_COLOR } from '../utils/grade'
import { Icon } from './Icon'

interface RouteCardsProps {
  routes: RouteOption[]
  selectedRouteId: string | null
  onSelect: (routeId: string) => void
}

/** 検索直後のルート比較カード。カード選択で地図・危険パネル側の表示ルートが切り替わる。 */
export function RouteCards({ routes, selectedRouteId, onSelect }: RouteCardsProps) {
  if (routes.length === 0) return null

  const minDistance = Math.min(...routes.map((route) => route.distance_m))

  return (
    <section className="route-cards-panel" aria-label="ルート比較">
      <div className="route-cards-title">
        <span className="label">ルート候補（{routes.length}件）</span>
      </div>
      <div className="route-cards-row" role="list">
        {routes.map((route) => {
          const selected = route.id === selectedRouteId
          const isShortest = route.distance_m === minDistance
          const hazardCount = route.hazard_points.length
          return (
            <button
              key={route.id}
              type="button"
              role="listitem"
              className={`route-card-item ${selected ? 'is-selected' : ''}`}
              aria-pressed={selected}
              onClick={() => onSelect(route.id)}
            >
              <div className="route-card-head">
                <span className="grade-badge" style={{ backgroundColor: GRADE_COLOR[route.safety_grade] }}>
                  {route.safety_grade}
                </span>
                <span className="route-card-score">安全度 {route.safety_score}</span>
              </div>
              <div className="route-card-chips">
                {route.kind === 'recommended' && <em className="chip chip-recommended">推奨</em>}
                {isShortest && <em className="chip chip-shortest">最短</em>}
              </div>
              <div className="route-card-metrics">
                <span>
                  <Icon name="clock" />
                  {formatDuration(route.duration_s)}
                </span>
                <span>
                  <Icon name="walk" />
                  {formatDistance(route.distance_m)}
                </span>
                <span>
                  <Icon name="warning" />
                  危険 {hazardCount}件
                </span>
              </div>
            </button>
          )
        })}
      </div>
    </section>
  )
}
