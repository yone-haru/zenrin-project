import { Icon } from './Icon'

/** 検索前に表示する使い方ガイド（3ステップ）。 */
export function EmptyStateCard() {
  return (
    <section className="empty-state-card">
      <span className="label">使い方</span>
      <ol>
        <li>
          <Icon name="pin" />
          <span>出発地と目的地を入力</span>
        </li>
        <li>
          <Icon name="search" />
          <span>ルートを検索</span>
        </li>
        <li>
          <Icon name="warning" />
          <span>危険地点を確認</span>
        </li>
      </ol>
    </section>
  )
}
