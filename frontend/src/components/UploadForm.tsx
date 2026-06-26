import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { uploadReport } from '../api/reports'

interface UploadFormProps {
  onUploadSuccess?: () => void
  selectedLocation?: { lat: number; lng: number } | null
}

export function UploadForm({ onUploadSuccess, selectedLocation }: UploadFormProps) {
  const [latitude, setLatitude] = useState('')
  const [longitude, setLongitude] = useState('')
  const [comment, setComment] = useState('')
  const [images, setImages] = useState<File[]>([])
  const [status, setStatus] = useState<'idle' | 'submitting' | 'success' | 'error'>('idle')
  const [errorMessage, setErrorMessage] = useState('')

  useEffect(() => {
    if (selectedLocation) {
      setLatitude(String(selectedLocation.lat))
      setLongitude(String(selectedLocation.lng))
    }
  }, [selectedLocation])

  function handleUseCurrentLocation() {
    if (!navigator.geolocation) {
      setStatus('error')
      setErrorMessage('このブラウザは位置情報の取得に対応していません')
      return
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLatitude(String(position.coords.latitude))
        setLongitude(String(position.coords.longitude))
      },
      () => {
        setStatus('error')
        setErrorMessage('現在地の取得に失敗しました')
      },
    )
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (images.length === 0) {
      setStatus('error')
      setErrorMessage('画像を1枚以上選択してください')
      return
    }

    setStatus('submitting')
    try {
      await uploadReport({
        latitude: Number(latitude),
        longitude: Number(longitude),
        comment,
        images,
      })
      setStatus('success')
      setLatitude('')
      setLongitude('')
      setComment('')
      setImages([])
      onUploadSuccess?.()
    } catch (error) {
      setStatus('error')
      setErrorMessage(error instanceof Error ? error.message : 'アップロードに失敗しました')
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <h2>危険箇所の通報</h2>
      <p>地図をクリック、または現在地ボタンで投稿位置を指定できます。</p>

      <div>
        <button type="button" onClick={handleUseCurrentLocation}>
          現在地を取得
        </button>
      </div>

      <div>
        <label>
          緯度
          <input
            type="number"
            step="any"
            required
            value={latitude}
            onChange={(event) => setLatitude(event.target.value)}
          />
        </label>
      </div>

      <div>
        <label>
          経度
          <input
            type="number"
            step="any"
            required
            value={longitude}
            onChange={(event) => setLongitude(event.target.value)}
          />
        </label>
      </div>

      <div>
        <label>
          画像（JPEG/PNG、複数選択可）
          <input
            type="file"
            accept="image/jpeg,image/png"
            multiple
            required
            onChange={(event) => setImages(Array.from(event.target.files ?? []))}
          />
        </label>
      </div>

      <div>
        <label>
          コメント（任意）
          <textarea value={comment} onChange={(event) => setComment(event.target.value)} />
        </label>
      </div>

      <p>
        ※ 投稿前に、画像内に他人の顔やナンバープレートなどが映り込んでいないかご確認ください。
      </p>

      <button type="submit" disabled={status === 'submitting'}>
        {status === 'submitting' ? '送信中...' : '送信'}
      </button>

      {status === 'success' && <p>送信しました</p>}
      {status === 'error' && <p role="alert">{errorMessage}</p>}
    </form>
  )
}
