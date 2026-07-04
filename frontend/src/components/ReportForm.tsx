import { useEffect, useMemo, useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'
import { useDialogA11y } from '../hooks/useDialogA11y'
import type { LatLng } from '../types'
import { Icon } from './Icon'

const MAX_IMAGES = 5
const ACCEPTED_TYPES = ['image/jpeg', 'image/png']

interface ReportFormProps {
  position: LatLng
  submitting: boolean
  error: string | null
  onCancel: () => void
  onSubmit: (data: { comment: string; images: File[] }) => void
}

export function ReportForm({ position, submitting, error, onCancel, onSubmit }: ReportFormProps) {
  const containerRef = useDialogA11y<HTMLFormElement>(true, onCancel)
  const [comment, setComment] = useState('')
  const [images, setImages] = useState<File[]>([])
  const [validationError, setValidationError] = useState<string | null>(null)

  const previewUrls = useMemo(() => images.map((file) => URL.createObjectURL(file)), [images])

  useEffect(() => {
    return () => {
      previewUrls.forEach((url) => URL.revokeObjectURL(url))
    }
  }, [previewUrls])

  function handleFilesChange(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? [])
    const invalid = files.some((file) => !ACCEPTED_TYPES.includes(file.type))
    if (invalid) {
      setValidationError('画像はJPEGまたはPNG形式のみ選択できます')
      return
    }
    if (files.length > MAX_IMAGES) {
      setValidationError(`写真は最大${MAX_IMAGES}枚まで選択できます`)
      setImages(files.slice(0, MAX_IMAGES))
      return
    }
    setValidationError(null)
    setImages(files)
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (images.length === 0) {
      setValidationError('写真を1枚以上選択してください')
      return
    }
    setValidationError(null)
    onSubmit({ comment, images })
  }

  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <form
        ref={containerRef}
        className="hazard-modal report-form"
        role="dialog"
        aria-modal="true"
        aria-labelledby="report-form-title"
        onClick={(event) => event.stopPropagation()}
        onSubmit={handleSubmit}
      >
        <div className="modal-strip" />
        <button className="close-button" type="button" aria-label="閉じる" onClick={onCancel}>
          <Icon name="close" />
        </button>
        <span className="label">危険箇所を報告</span>
        <h2 id="report-form-title">この地点の危険箇所を投稿</h2>
        <p className="report-position">
          指定位置: {position.lat.toFixed(5)}, {position.lng.toFixed(5)}
        </p>

        <section>
          <h3>写真（最大{MAX_IMAGES}枚・JPEG/PNG）</h3>
          <label className="file-drop">
            <input
              type="file"
              accept="image/jpeg,image/png"
              multiple
              aria-label="危険箇所の写真を選択"
              onChange={handleFilesChange}
            />
            <Icon name="camera" />
            写真を選択
          </label>
          {previewUrls.length > 0 && (
            <div className="report-photo-grid">
              {previewUrls.map((url, index) => (
                <img key={url} src={url} alt={`選択した写真 ${index + 1}`} />
              ))}
            </div>
          )}
        </section>

        <section>
          <h3>コメント（任意）</h3>
          <textarea
            className="report-comment-input"
            value={comment}
            aria-label="コメント"
            placeholder="歩道が狭い、見通しが悪い、など状況を入力してください"
            onChange={(event) => setComment(event.target.value)}
          />
        </section>

        <p className="report-privacy-note">
          ※ 投稿前に、画像内に他人の顔やナンバープレートなどが映り込んでいないかご確認ください。
        </p>

        {(validationError || error) && (
          <p className="report-error" role="alert">
            {validationError ?? error}
          </p>
        )}

        <footer>
          <button type="button" onClick={onCancel} disabled={submitting}>
            キャンセル
          </button>
          <button className="primary" type="submit" disabled={submitting} aria-busy={submitting}>
            {submitting ? <span className="spinner" aria-hidden="true" /> : null}
            {submitting ? '送信中...' : '送信する'}
          </button>
        </footer>
      </form>
    </div>
  )
}
