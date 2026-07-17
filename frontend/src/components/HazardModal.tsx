import type { CSSProperties } from 'react'
import { API_BASE_URL } from '../api/reports'
import { useDialogA11y } from '../hooks/useDialogA11y'
import type { SelectedDetail } from '../types'
import { formatDistance } from '../utils/format'
import { STATUS_LABEL } from '../utils/reportStatus'
import { riskColor, riskSoftColor } from '../utils/riskColor'
import { Icon } from './Icon'
import { StreetViewPreview } from './StreetViewPreview'

interface HazardModalProps {
  detail: SelectedDetail
  onClose: () => void
  onLocate: () => void
}

const HIGHWAY_LABEL: Record<string, string> = {
  motorway: '高速道路',
  trunk: '幹線道路（国道級）',
  primary: '主要幹線道路',
  secondary: '幹線道路',
  tertiary: '主要な生活道路',
  unclassified: '一般道路',
  residential: '生活道路',
  service: '通路・私道',
  footway: '歩道',
  path: '小道',
  pedestrian: '歩行者専用道路',
  living_street: '歩行者優先道路',
}

const SIDEWALK_LABEL: Record<string, string> = {
  both: '両側にあり',
  left: '片側のみ',
  right: '片側のみ',
  separate: '分離歩道あり',
  no: 'なし',
  none: 'なし',
}

export function HazardModal({ detail, onClose, onLocate }: HazardModalProps) {
  const containerRef = useDialogA11y<HTMLDivElement>(true, onClose)

  const score = detail.kind === 'hazard' ? detail.hazard.risk_score : detail.report.risk_score
  const color = riskColor(score)
  const softColor = riskSoftColor(score)
  const title =
    detail.kind === 'hazard'
      ? `${detail.hazard.title ?? '危険地点'}付近`
      : (detail.report.description_ai?.slice(0, 40) ?? '投稿された危険箇所')

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <article
        ref={containerRef}
        className="hazard-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="hazard-modal-title"
        style={{ '--risk-color': color } as CSSProperties}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="modal-strip" />
        <button className="close-button" type="button" aria-label="閉じる" onClick={onClose}>
          <Icon name="close" />
        </button>
        <span className="label">危険度</span>
        <div className="modal-score">
          <strong>{score ?? '?'}</strong>
          <span>
            {[1, 2, 3, 4, 5].map((value) => (
              <i key={value} className={score !== null && value <= score ? 'filled' : ''} />
            ))}
          </span>
        </div>
        <h2 id="hazard-modal-title">{title}</h2>

        {detail.kind === 'hazard' ? (
          <>
            <section>
              <h3>現地の様子</h3>
              <StreetViewPreview lat={detail.hazard.latitude} lng={detail.hazard.longitude} />
            </section>
            <section>
              <h3>危険要因</h3>
              <div className="factor-row">
                {detail.hazard.risk_factors.map((factor) => (
                  <span key={factor} style={{ backgroundColor: softColor, color }}>
                    {factor}
                  </span>
                ))}
              </div>
            </section>
            <section>
              <h3>事故データ</h3>
              <div className="accident-row">
                <Icon name="warning" />
                {detail.hazard.accident_count > 0
                  ? `付近で${detail.hazard.accident_count}件の交通事故が発生（警察庁オープンデータ）`
                  : '事故データの登録なし（警察庁オープンデータ）'}
              </div>
            </section>
            <section>
              <h3>道路情報</h3>
              <dl className="road-info">
                <div>
                  <dt>道路種別</dt>
                  <dd>
                    {detail.hazard.osm_tags.highway
                      ? (HIGHWAY_LABEL[detail.hazard.osm_tags.highway] ?? detail.hazard.osm_tags.highway)
                      : '不明'}
                  </dd>
                </div>
                <div>
                  <dt>歩道</dt>
                  <dd>
                    {detail.hazard.osm_tags.sidewalk
                      ? (SIDEWALK_LABEL[detail.hazard.osm_tags.sidewalk] ?? detail.hazard.osm_tags.sidewalk)
                      : '情報なし'}
                  </dd>
                </div>
              </dl>
            </section>
          </>
        ) : (
          <>
            {detail.report.image_urls.length > 0 && (
              <section>
                <h3>写真</h3>
                <div className="report-photo-grid">
                  {detail.report.image_urls.map((url) => (
                    <img key={url} src={`${API_BASE_URL}${url}`} alt="投稿された危険箇所の写真" loading="lazy" />
                  ))}
                </div>
              </section>
            )}
            <section>
              <h3>AIによる説明</h3>
              <div className="accident-row">
                <Icon name="warning" />
                {detail.report.description_ai ?? '解析中です'}
              </div>
            </section>
            {detail.report.comment_user && (
              <section>
                <h3>投稿コメント</h3>
                <p className="report-comment">{detail.report.comment_user}</p>
              </section>
            )}
            <section>
              <h3>投稿情報</h3>
              <dl className="road-info">
                <div>
                  <dt>状態</dt>
                  <dd>{STATUS_LABEL[detail.report.status] ?? detail.report.status}</dd>
                </div>
                <div>
                  <dt>投稿日時</dt>
                  <dd>{new Date(detail.report.created_at).toLocaleString('ja-JP')}</dd>
                </div>
                {detail.distanceFromRouteM !== undefined && (
                  <div>
                    <dt>ルートからの距離</dt>
                    <dd>{formatDistance(detail.distanceFromRouteM)}</dd>
                  </div>
                )}
              </dl>
            </section>
          </>
        )}

        <footer>
          <button type="button" onClick={onClose}>
            閉じる
          </button>
          <button className="primary" type="button" onClick={onLocate}>
            地図で確認
          </button>
        </footer>
      </article>
    </div>
  )
}
