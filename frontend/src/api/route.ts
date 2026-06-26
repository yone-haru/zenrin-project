import { API_BASE_URL } from './reports'
import type { Report } from './reports'

export interface GeocodeResult {
  name: string
  latitude: number
  longitude: number
}

export interface RoutePoint {
  latitude: number
  longitude: number
}

export interface RouteResult {
  points: RoutePoint[]
  distance_m: number
  duration_s: number
}

export interface RouteDangerReport {
  report: Report
  distance_from_route_m: number
}

export interface RouteSearchResult {
  route: RouteResult
  danger_reports: RouteDangerReport[]
}

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

export interface RouteResponse {
  route_geometry: {
    type: 'LineString'
    coordinates: [number, number][]
  }
  distance_m: number
  duration_s: number
  hazard_points: HazardPoint[]
}

export interface GeocodeAddressResult {
  lat: number
  lng: number
  display_name: string
}

export async function geocode(query: string): Promise<GeocodeResult[]> {
  const response = await fetch(
    `${API_BASE_URL}/api/route/geocode?query=${encodeURIComponent(query)}`,
  )

  if (!response.ok) {
    throw new Error('地点検索に失敗しました')
  }

  return response.json()
}

export interface SearchRouteParams {
  fromLat: number
  fromLng: number
  toLat: number
  toLng: number
}

export async function searchRoute(params: SearchRouteParams): Promise<RouteSearchResult> {
  const query = new URLSearchParams({
    from_lat: String(params.fromLat),
    from_lng: String(params.fromLng),
    to_lat: String(params.toLat),
    to_lng: String(params.toLng),
  })

  const response = await fetch(`${API_BASE_URL}/api/route/search?${query}`)

  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail ?? 'ルート検索に失敗しました')
  }

  return response.json()
}

export async function geocodeAddress(query: string): Promise<GeocodeAddressResult> {
  const response = await fetch(`${API_BASE_URL}/api/geocode?q=${encodeURIComponent(query)}`)

  if (!response.ok) {
    throw new Error('地点検索に失敗しました')
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
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail ?? 'ルート検索に失敗しました')
  }

  return response.json()
}
