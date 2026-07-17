import type { HazardPoint, RouteOption } from '../api/route'
import type { Report } from '../api/reports'
import type { LatLng, Point } from '../types'

/**
 * MapView（Leaflet版）・GoogleMapView（Google Maps Platform版）共通のprops型。
 * App.tsx はどちらのコンポーネントにも同一のpropsを渡して差し替えられる（plan v3.2）。
 */
export interface MapViewProps {
  origin: Point | null
  destination: Point | null
  routes: RouteOption[]
  selectedRouteId: string | null
  onSelectRoute: (routeId: string) => void
  hazards: HazardPoint[]
  selectedHazardId: string | null
  onSelectHazard: (hazard: HazardPoint) => void
  reports: Report[]
  selectedReportId: string | null
  onSelectReport: (report: Report) => void
  reportDraft: LatLng | null
  onMapPick: (lat: number, lng: number) => void
  isSearching: boolean
}
