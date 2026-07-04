import { API_BASE_URL } from './reports'
import type { Report } from './reports'

export interface AddressPoint {
  lat: number
  lng: number
  address?: string
}

export interface HazardPoint {
  id: string
  latitude: number
  longitude: number
  risk_score: number
  risk_factors: string[]
  accident_count: number
  osm_tags: Record<string, string>
  title?: string | null
  distance_from_origin_m?: number | null
}

export interface RouteDangerReport {
  report: Report
  distance_from_route_m: number
}

export interface RouteResponse {
  route_geometry: {
    type: 'LineString'
    coordinates: [number, number][]
  }
  distance_m: number
  duration_s: number
  hazard_points: HazardPoint[]
  danger_reports: RouteDangerReport[]
}

export interface GeocodeResult {
  name: string
  lat: number
  lng: number
}

async function parseErrorDetail(response: Response, fallback: string): Promise<string> {
  const body = await response.json().catch(() => null)
  return (body && typeof body.detail === 'string' && body.detail) || fallback
}

export async function geocode(query: string, limit = 5): Promise<GeocodeResult[]> {
  const trimmed = query.trim()
  if (!trimmed) return []

  const params = new URLSearchParams({ q: trimmed, limit: String(limit) })
  const response = await fetch(`${API_BASE_URL}/api/geocode?${params.toString()}`)

  if (!response.ok) {
    throw new Error(await parseErrorDetail(response, '地点検索に失敗しました'))
  }

  return response.json()
}

export async function createRoute(origin: AddressPoint, destination: AddressPoint): Promise<RouteResponse> {
  const response = await fetch(`${API_BASE_URL}/api/route`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ origin, destination }),
  })

  if (!response.ok) {
    throw new Error(await parseErrorDetail(response, 'ルート検索に失敗しました'))
  }

  return response.json()
}
