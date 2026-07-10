import { useState } from 'react'
import { API_BASE_URL, updateReportStatus } from '../api/reports'
import type { Report, ReportStatus } from '../api/reports'
import { useDialogA11y } from '../hooks/useDialogA11y'
import { STATUS_LABEL } from '../utils/reportStatus'
import { Icon } from './Icon'

const ADMIN_TOKEN_STORAGE_KEY = 'admin_token'

interface AdminPanelProps {
  reports: Report[]
  onUpdateReport: (report: Report) => void
  onClose: () => void
}

/** 自治体職員向けの通報管理パネル。ADMIN_TOKENは sessionStorage に保持する（画面を閉じても保持、タブを閉じると消える）。 */
export function AdminPanel({ reports, onUpdateReport, onClose }: AdminPanelProps) {
  const containerRef = useDialogA11y<HTMLDivElement>(true, onClose)
  const [token, setToken] = useState(() => sessionStorage.getItem(ADMIN_TOKEN_STORAGE_KEY) ?? '')
  const [error, setError] = useState<string | null>(null)
  const [updatingId, setUpdatingId] = useState<string | null>(null)

  function handleTokenChange(value: string) {
    setToken(value)
    sessionStorage.setItem(ADMIN_TOKEN_STORAGE_KEY, value)
  }

  async function handleStatusChange(report: Report, status: ReportStatus) {
    if (!token.trim()) {
      setError('トークンを入力してください')
      return
    }
    setError(null)
    setUpdatingId(report.id)
    try {
      const updated = await updateReportStatus(report.id, status, token.trim())
      onUpdateReport(updated)
    } catch (err) {
      setError(err instanceof Error ? err.message : '更新に失敗しました')
    } finally {
      setUpdatingId(null)
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <article
        ref={containerRef}
        className="hazard-modal admin-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="admin-panel-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="modal-strip admin-strip" />
        <button className="close-button" type="button" aria-label="閉じる" onClick={onClose}>
          <Icon name="close" />
        </button>
        <span className="label">管理パネル</span>
        <h2 id="admin-panel-title">通報の確認・却下</h2>

        <section>
          <h3>管理者トークン</h3>
          <input
            type="password"
            className="admin-token-input"
            value={token}
            placeholder="ADMIN_TOKEN を入力"
            aria-label="管理者トークン"
            autoComplete="off"
            onChange={(event) => handleTokenChange(event.target.value)}
          />
        </section>

        {error && (
          <p className="report-error" role="alert">
            {error}
          </p>
        )}

        <section>
          <h3>通報一覧（{reports.length}件）</h3>
          <div className="admin-report-list">
            {reports.length === 0 && <p className="hazard-empty">通報はまだありません</p>}
            {reports.map((report) => (
              <div key={report.id} className="admin-report-row">
                {report.image_urls[0] ? (
                  <img src={`${API_BASE_URL}${report.image_urls[0]}`} alt="通報された危険箇所" loading="lazy" />
                ) : (
                  <div className="admin-report-thumb-empty" aria-hidden="true" />
                )}
                <div className="admin-report-info">
                  <span className={`status-chip status-${report.status}`}>
                    {STATUS_LABEL[report.status] ?? report.status}
                  </span>
                  <p>{report.description_ai ?? report.comment_user ?? '説明なし'}</p>
                  <span className="admin-report-date">{new Date(report.created_at).toLocaleString('ja-JP')}</span>
                </div>
                <div className="admin-report-actions">
                  <button
                    type="button"
                    className="confirm-button"
                    disabled={updatingId === report.id}
                    aria-busy={updatingId === report.id}
                    onClick={() => handleStatusChange(report, 'confirmed')}
                  >
                    <Icon name="check" />
                    確認
                  </button>
                  <button
                    type="button"
                    className="reject-button"
                    disabled={updatingId === report.id}
                    aria-busy={updatingId === report.id}
                    onClick={() => handleStatusChange(report, 'rejected')}
                  >
                    <Icon name="close" />
                    却下
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      </article>
    </div>
  )
}
