import type { HazardPoint } from './api/route'
import type { Report } from './api/reports'

export type Target = 'origin' | 'destination'

export interface Point {
  lat: number
  lng: number
  address: string
}

export interface LatLng {
  lat: number
  lng: number
}

export type SelectedDetail =
  | { kind: 'hazard'; hazard: HazardPoint }
  | { kind: 'report'; report: Report; distanceFromRouteM?: number }
