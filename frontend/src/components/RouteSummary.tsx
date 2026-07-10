import type { SafetyGrade } from '../api/route'
import { formatDistance, formatDuration } from '../utils/format'
import { GRADE_COLOR } from '../utils/grade'
import { Icon } from './Icon'

interface RouteSummaryProps {
  distanceM: number
  durationS: number
  hazardCount: number
  grade: SafetyGrade
  score: number
  onShare: () => void
}

export function RouteSummary({ distanceM, durationS, hazardCount, grade, score, onShare }: RouteSummaryProps) {
  const color = GRADE_COLOR[grade]
  return (
    <section className="route-card">
      <div className="route-card-top">
        <span className="grade-badge grade-badge-lg" style={{ backgroundColor: color }}>
          {grade}
        </span>
        <div className="route-card-score-block">
          <span className="label">安全スコア</span>
          <strong style={{ color }}>
            {score}
            <span className="score-max">/100</span>
          </strong>
        </div>
        <button type="button" className="share-button" onClick={onShare}>
          <Icon name="share" />
          共有
        </button>
      </div>
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
