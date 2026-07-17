import { useDialogA11y } from '../hooks/useDialogA11y'
import { RANK_TABLE } from '../utils/grade'
import { riskColor } from '../utils/riskColor'
import { Icon } from './Icon'

const CONTACT_EMAIL = import.meta.env.VITE_CONTACT_EMAIL ?? ''
const POINT_RISK_SCORES = [1, 2, 3, 4, 5]

interface AboutModalProps {
  onClose: () => void
}

/** 検索カードの「？」ボタンから開くヘルプモーダル（plan v3.3）。 */
export function AboutModal({ onClose }: AboutModalProps) {
  const containerRef = useDialogA11y<HTMLDivElement>(true, onClose)

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <article
        ref={containerRef}
        className="hazard-modal about-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="about-modal-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="modal-strip about-strip" />
        <button className="close-button" type="button" aria-label="閉じる" onClick={onClose}>
          <Icon name="close" />
        </button>
        <span className="label">ヘルプ</span>
        <h2 id="about-modal-title">このマップについて</h2>

        <section>
          <h3>使い方</h3>
          <ol className="about-steps">
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

        <section>
          <h3>凡例</h3>
          <p className="about-legend-caption">地点の危険度（1〜5、数字が大きいほど危険）</p>
          <div className="about-point-legend">
            {POINT_RISK_SCORES.map((score) => (
              <span key={score} className="about-point-chip">
                <i style={{ backgroundColor: riskColor(score) }} />
                {score}
              </span>
            ))}
          </div>
          <p className="about-legend-caption">ルートの危険度ランク</p>
          <div className="about-rank-legend">
            {RANK_TABLE.map((rank) => (
              <span
                key={rank.label}
                className="rank-badge"
                style={{ backgroundColor: `${rank.color}1a`, color: rank.color }}
              >
                {rank.label}
              </span>
            ))}
          </div>
        </section>

        <section>
          <h3>データ出典・更新時期</h3>
          <ul className="about-source-list">
            <li>警察庁 交通事故オープンデータ（2022〜2023年・長崎周辺）</li>
            <li>OpenStreetMap 道路データ（リアルタイム取得）</li>
            <li>Google Maps・ストリートビュー（APIキー設定時のみ）</li>
            <li>住民の写真通報</li>
          </ul>
        </section>

        <section>
          <h3>運用・お問い合わせ</h3>
          <p className="about-contact-text">本マップは授業プロジェクトの試作版です。ご意見は運用者までお寄せください。</p>
          {CONTACT_EMAIL && (
            <a className="about-contact-link" href={`mailto:${CONTACT_EMAIL}`}>
              <Icon name="mail" />
              {CONTACT_EMAIL}
            </a>
          )}
        </section>

        <footer>
          <button className="primary" type="button" onClick={onClose}>
            閉じる
          </button>
        </footer>
      </article>
    </div>
  )
}
