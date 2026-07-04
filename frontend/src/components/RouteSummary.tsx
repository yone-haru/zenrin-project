import { formatDistance, formatDuration } from '../utils/format'
import { Icon } from './Icon'

interface RouteSummaryProps {
  distanceM: number
  durationS: number
  hazardCount: number
}

export function RouteSummary({ distanceM, durationS, hazardCount }: RouteSummaryProps) {
  return (
    <section className="route-card">
      <span className="label">ルート情報</span>
      <div className="route-metrics">
        <span>
          <Icon name="walk" />
          {formatDistance(distanceM)}
        </span>
        <span>
          <Icon name="clock" />
          {formatDuration(durationS)}
        </span>
        <strong>危険箇所 {hazardCount}件</strong>
      </div>
    </section>
  )
}
