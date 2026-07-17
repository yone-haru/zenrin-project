export interface HazardListItem {
  key: string
  color: string
  textColor: string
  scoreLabel: string
  title: string
  distanceText?: string
  tags: string[]
  sourceLabel: string
  onSelect: () => void
}

interface HazardListProps {
  items: HazardListItem[]
  selectedKey: string | null
}

/** 危険箇所一覧の中身（縦スクロールリスト）。ボトムシートの expanded 状態に埋め込む。 */
export function HazardList({ items, selectedKey }: HazardListProps) {
  return (
    <div className="hazard-list">
      {items.length === 0 && <p className="hazard-empty">危険箇所は見つかりませんでした</p>}
      {items.map((item) => (
        <button
          key={item.key}
          className={`hazard-item ${item.key === selectedKey ? 'is-selected' : ''}`}
          style={{ borderLeftColor: item.color }}
          type="button"
          onClick={item.onSelect}
        >
          <span className="score-badge" style={{ backgroundColor: item.color, color: item.textColor }}>
            {item.scoreLabel}
          </span>
          <span className="hazard-summary">
            <span className="hazard-title">
              {item.title}
              <em className="source-chip">{item.sourceLabel}</em>
            </span>
            {item.distanceText && <span className="hazard-distance">{item.distanceText}</span>}
            <span className="tag-row">
              {item.tags.map((tag) => (
                <span key={tag}>{tag}</span>
              ))}
            </span>
          </span>
          <span className="chevron" aria-hidden="true">
            ›
          </span>
        </button>
      ))}
    </div>
  )
}
