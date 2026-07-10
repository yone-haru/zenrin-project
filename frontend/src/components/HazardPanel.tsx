import { useState } from 'react'
import { Icon } from './Icon'

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

interface HazardPanelProps {
  items: HazardListItem[]
  selectedKey: string | null
  offsetForAdminButton?: boolean
}

export function HazardPanel({ items, selectedKey, offsetForAdminButton = false }: HazardPanelProps) {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <aside
      className={`hazard-panel ${collapsed ? 'is-collapsed' : ''} ${offsetForAdminButton ? 'with-admin-offset' : ''}`}
    >
      <div className="panel-title">
        <span className="sheet-handle" aria-hidden="true" />
        <h2>危険箇所一覧</h2>
        <span className="panel-count">{items.length}件</span>
        <button
          type="button"
          className="panel-collapse-toggle"
          aria-expanded={!collapsed}
          aria-label={collapsed ? '危険箇所一覧を開く' : '危険箇所一覧を閉じる'}
          onClick={() => setCollapsed((value) => !value)}
        >
          <Icon name="chevronDown" />
        </button>
      </div>
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
    </aside>
  )
}
