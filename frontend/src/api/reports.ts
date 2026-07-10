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

async function parseErrorDetail(response: Response, fallback: string): Promise<string> {
  const body = await response.json().catch(() => null)
  return (body && typeof body.detail === 'string' && body.detail) || fallback
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
    throw new Error(await parseErrorDetail(response, '投稿に失敗しました'))
  }

  return response.json()
}

export async function fetchReports(): Promise<Report[]> {
  const response = await fetch(`${API_BASE_URL}/api/reports`)

  if (!response.ok) {
    throw new Error(await parseErrorDetail(response, '地点情報の取得に失敗しました'))
  }

  return response.json()
}

export type ReportStatus = 'unconfirmed' | 'confirmed' | 'rejected'

/**
 * 管理者用: 通報のステータスを更新する。X-Admin-Token が不一致/未設定だと 401 になる
 * （backend/.claude/plan.md 契約 v3 参照）。
 */
export async function updateReportStatus(id: string, status: ReportStatus, token: string): Promise<Report> {
  const response = await fetch(`${API_BASE_URL}/api/reports/${id}/status`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'X-Admin-Token': token,
    },
    body: JSON.stringify({ status }),
  })

  if (response.status === 401) {
    throw new Error('トークンが正しくありません')
  }

  if (!response.ok) {
    throw new Error(await parseErrorDetail(response, 'ステータスの更新に失敗しました'))
  }

  return response.json()
}
