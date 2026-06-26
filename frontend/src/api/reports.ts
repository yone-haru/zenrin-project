export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export interface Report {
  id: string
  latitude: number
  longitude: number
  image_urls: string[]
  description_ai: string | null
  risk_score: number | null
  comment_user: string | null
  status: string
  created_at: string
  source: string
}

export interface UploadReportParams {
  latitude: number
  longitude: number
  comment: string
  images: File[]
}

export async function uploadReport(params: UploadReportParams): Promise<Report> {
  const formData = new FormData()
  formData.append('latitude', String(params.latitude))
  formData.append('longitude', String(params.longitude))
  if (params.comment) {
    formData.append('comment', params.comment)
  }
  for (const image of params.images) {
    formData.append('images', image)
  }

  const response = await fetch(`${API_BASE_URL}/api/reports`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail ?? 'アップロードに失敗しました')
  }

  return response.json()
}

export async function fetchReports(): Promise<Report[]> {
  const response = await fetch(`${API_BASE_URL}/api/reports`)

  if (!response.ok) {
    throw new Error('地点情報の取得に失敗しました')
  }

  return response.json()
}
